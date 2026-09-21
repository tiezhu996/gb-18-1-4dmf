"""模拟考试接口级测试：组卷、保存进度、到点自动结算、重复/并发交卷。"""
import asyncio
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

import app.core.database as database
from app.main import app
from app.modules.auth.dependencies import get_current_user

USER_ID = "user-api-1"
SUBJECT_ID = "subject-api-1"


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["test_exam_api"]
    monkeypatch.setattr(database, "db", db)

    async def noop():
        return None

    monkeypatch.setattr("app.main.init_db", noop)
    monkeypatch.setattr("app.main.init_redis", noop)

    app.dependency_overrides[get_current_user] = lambda: {"_id": USER_ID}
    yield db
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def questions(mock_db):
    docs = []
    for i in range(3):
        docs.append({
            "_id": ObjectId(),
            "subject_id": SUBJECT_ID,
            "type": "single_choice",
            "content": f"题目{i + 1}",
            "options": [
                {"key": "A", "content": "选项A"},
                {"key": "B", "content": "选项B"}
            ],
            "correct_answer": "A",
            "difficulty": "easy",
            "knowledge_ids": [],
            "explanation": f"解析{i + 1}"
        })
    await mock_db.questions.insert_many(docs)
    return docs


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _start_exam(client) -> dict:
    resp = await client.post("/api/exam/start", json={
        "name": "模拟考试",
        "subject_id": SUBJECT_ID,
        "question_count": 3,
        "duration_minutes": 30
    })
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_full_exam_flow(client, questions):
    data = await _start_exam(client)
    session_id = data["session_id"]
    assert data["remaining_seconds"] > 0
    assert data["is_submitted"] is False
    assert len(data["questions"]) == 3

    qid = data["questions"][0]["id"]

    # 自动保存答题进度
    resp = await client.put(f"/api/exam/{session_id}/answers", json={
        "answers": {qid: "B"}
    })
    assert resp.status_code == 200
    assert resp.json()["saved"] is True

    # 刷新恢复：剩余时间与已保存答案
    resp = await client.get(f"/api/exam/{session_id}")
    assert resp.status_code == 200
    restored = resp.json()
    assert restored["answers"][qid] == "B"
    assert restored["remaining_seconds"] > 0
    assert len(restored["questions"]) == 3

    # 手动交卷
    answers = {q["id"]: "A" for q in data["questions"]}
    resp = await client.post("/api/exam/submit", json={
        "session_id": session_id,
        "answers": answers
    })
    assert resp.status_code == 200
    result = resp.json()
    assert result["score"] == 100
    assert result["correct_count"] == 3
    assert result["accuracy"] == result["score"]
    assert len(result["details"]) == 3

    # 重复交卷回读首次报告
    resp = await client.post("/api/exam/submit", json={
        "session_id": session_id,
        "answers": {}
    })
    assert resp.status_code == 200
    again = resp.json()
    assert again["score"] == 100
    assert again["submitted_at"] == result["submitted_at"]

    # 历史报告可读
    resp = await client.get(f"/api/exam/result/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["score"] == 100

    resp = await client.get("/api/exam/history/list")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_auto_settle_after_deadline(client, mock_db, questions):
    data = await _start_exam(client)
    session_id = data["session_id"]
    qid = data["questions"][0]["id"]

    await client.put(f"/api/exam/{session_id}/answers", json={
        "answers": {qid: "A"}
    })

    # 将考试开始时间改到截止时间之后
    await mock_db.exam_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"start_time": datetime.utcnow() - timedelta(minutes=35)}}
    )

    # 到点后刷新页面：不再下发题目，直接可查看结果
    resp = await client.get(f"/api/exam/{session_id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["is_submitted"] is True
    assert payload["remaining_seconds"] == 0
    assert payload["questions"] == []

    # 自动结算结果：1 对 2 错（未答按错误计）
    resp = await client.get(f"/api/exam/result/{session_id}")
    assert resp.status_code == 200
    result = resp.json()
    assert result["correct_count"] == 1
    assert result["score"] == 33.3
    assert result["accuracy"] == 33.3
    assert result["duration_used"] == 30 * 60
    unanswered = [d for d in result["details"] if d["user_answer"] is None]
    assert len(unanswered) == 2
    assert all(not d["is_correct"] for d in unanswered)

    # 到点后保存答案被拒绝
    resp = await client.put(f"/api/exam/{session_id}/answers", json={
        "answers": {qid: "B"}
    })
    assert resp.status_code == 200
    assert resp.json()["saved"] is False

    # 迟到交卷不能改变首次结算结果
    resp = await client.post("/api/exam/submit", json={
        "session_id": session_id,
        "answers": {q["id"]: "A" for q in data["questions"]}
    })
    assert resp.status_code == 200
    assert resp.json()["score"] == 33.3


@pytest.mark.asyncio
async def test_concurrent_submit_via_api(client, questions):
    data = await _start_exam(client)
    session_id = data["session_id"]
    answers = {q["id"]: "A" for q in data["questions"]}

    responses = await asyncio.gather(*[
        client.post("/api/exam/submit", json={
            "session_id": session_id,
            "answers": answers
        })
        for _ in range(5)
    ])

    results = [r.json() for r in responses]
    assert all(r.status_code == 200 for r in responses)
    assert {r["score"] for r in results} == {100}
    assert len({r["submitted_at"] for r in results}) == 1
