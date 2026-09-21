"""模拟考试到点自动结算的测试。

覆盖：
- 到点未交卷按已保存答案自动结算，未答题按错误计
- 结算只发生一次：重复/并发交卷回读首次报告
- 超过宽限期的迟到交卷不覆盖首次结算结果
- 刷新恢复：返回服务端剩余时间与已保存答案
- 历史报告保持可读，成绩/正确率/逐题解析一致
"""
import asyncio
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

import app.core.database as database
from app.modules.exam.service import ExamService, SUBMIT_GRACE_SECONDS

USER_ID = "user-1"
SUBJECT_ID = "subject-1"


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["test_exam"]
    monkeypatch.setattr(database, "db", db)
    return db


@pytest_asyncio.fixture
async def questions(mock_db):
    docs = []
    for i in range(4):
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


async def _make_expired_session(db, questions, answers=None, duration_minutes=30):
    """直接构造一个已经超过截止时间的未交卷考试会话。"""
    now = datetime.utcnow()
    session = {
        "name": "模拟考试",
        "user_id": USER_ID,
        "subject_id": SUBJECT_ID,
        "question_ids": [str(q["_id"]) for q in questions],
        "duration_minutes": duration_minutes,
        "start_time": now - timedelta(minutes=duration_minutes + 5),
        "end_time": None,
        "answers": answers or {},
        "is_submitted": False,
        "score": None,
        "total_questions": len(questions),
        "correct_count": None
    }
    result = await db.exam_sessions.insert_one(session)
    return str(result.inserted_id)


@pytest.mark.asyncio
async def test_manual_submit_before_deadline(questions):
    session = await ExamService.create_exam(
        user_id=USER_ID, name="模拟考试", subject_id=SUBJECT_ID,
        question_count=4, duration_minutes=30
    )
    answers = {str(q["_id"]): "A" for q in questions}
    result = await ExamService.submit_exam(session["id"], USER_ID, answers)

    assert result["score"] == 100
    assert result["correct_count"] == 4
    assert result["accuracy"] == result["score"]
    assert len(result["details"]) == 4
    assert all(d["is_correct"] for d in result["details"])


@pytest.mark.asyncio
async def test_auto_settle_on_read_after_deadline(mock_db, questions):
    # 已保存 2 题答案（1 对 1 错），其余未答
    saved = {
        str(questions[0]["_id"]): "A",
        str(questions[1]["_id"]): "B"
    }
    session_id = await _make_expired_session(mock_db, questions, answers=saved)

    # 到点后访问考试（刷新页面）触发自动结算
    session = await ExamService.get_exam(session_id, USER_ID)
    assert session["is_submitted"] is True
    assert session["correct_count"] == 1
    assert session["score"] == 25.0
    # 交卷时间按截止时间计，而不是触发结算的时间
    assert session["duration_used"] == 30 * 60

    result = await ExamService.get_result(session_id, USER_ID)
    assert result["score"] == 25.0
    assert result["accuracy"] == 25.0
    assert result["total_questions"] == 4
    assert result["correct_count"] == 1
    # 未答题按错误计，且逐题解析完整
    by_qid = {d["question_id"]: d for d in result["details"]}
    assert by_qid[str(questions[0]["_id"])]["is_correct"] is True
    assert by_qid[str(questions[1]["_id"])]["is_correct"] is False
    assert by_qid[str(questions[2]["_id"])]["is_correct"] is False
    assert by_qid[str(questions[2]["_id"])]["user_answer"] is None
    assert by_qid[str(questions[3]["_id"])]["explanation"] == "解析4"


@pytest.mark.asyncio
async def test_repeated_submit_returns_first_report(mock_db, questions):
    saved = {str(questions[0]["_id"]): "A"}
    session_id = await _make_expired_session(mock_db, questions, answers=saved)

    first = await ExamService.submit_exam(session_id, USER_ID, dict(saved))
    # 重复交卷（甚至携带不同答案）必须回读首次报告
    all_correct = {str(q["_id"]): "A" for q in questions}
    second = await ExamService.submit_exam(session_id, USER_ID, all_correct)

    assert first["score"] == 25.0
    assert second["score"] == first["score"]
    assert second["correct_count"] == first["correct_count"]
    assert second["submitted_at"] == first["submitted_at"]
    assert second["details"] == first["details"]


@pytest.mark.asyncio
async def test_concurrent_submit_settles_only_once(mock_db, questions):
    saved = {str(questions[0]["_id"]): "A"}
    session_id = await _make_expired_session(mock_db, questions, answers=saved)

    results = await asyncio.gather(*[
        ExamService.submit_exam(session_id, USER_ID, dict(saved))
        for _ in range(5)
    ])

    scores = {r["score"] for r in results}
    submitted_ats = {r["submitted_at"] for r in results}
    assert scores == {25.0}
    assert len(submitted_ats) == 1

    # 错题只被记录一次（结算只发生一次）
    error_count = await mock_db.errors.count_documents({"user_id": USER_ID})
    assert error_count == 3
    async for err in mock_db.errors.find({"user_id": USER_ID}):
        assert err["wrong_count"] == 1


@pytest.mark.asyncio
async def test_late_submit_beyond_grace_uses_saved_answers(mock_db, questions):
    saved = {str(questions[0]["_id"]): "A"}
    session_id = await _make_expired_session(mock_db, questions, answers=saved)

    # 到点很久之后才交卷：按已保存答案结算，迟到答案不生效
    late_answers = {str(q["_id"]): "A" for q in questions}
    result = await ExamService.submit_exam(session_id, USER_ID, late_answers)

    assert result["score"] == 25.0
    assert result["correct_count"] == 1


@pytest.mark.asyncio
async def test_save_answers_and_restore(mock_db, questions):
    session = await ExamService.create_exam(
        user_id=USER_ID, name="模拟考试", subject_id=SUBJECT_ID,
        question_count=4, duration_minutes=30
    )
    session_id = session["id"]
    qid = str(questions[0]["_id"])

    saved = await ExamService.save_answers(session_id, USER_ID, {qid: "B"})
    assert saved["saved"] is True
    assert saved["is_submitted"] is False
    assert 0 < saved["remaining_seconds"] <= 30 * 60

    # 刷新后恢复：剩余时间与已保存答案
    restored = await ExamService.get_exam(session_id, USER_ID)
    assert restored["answers"][qid] == "B"
    assert restored["is_submitted"] is False

    # 到点后保存被拒绝并触发自动结算
    await mock_db.exam_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"start_time": datetime.utcnow() - timedelta(minutes=35)}}
    )
    rejected = await ExamService.save_answers(session_id, USER_ID, {qid: "A"})
    assert rejected["saved"] is False
    assert rejected["is_submitted"] is True

    result = await ExamService.get_result(session_id, USER_ID)
    by_qid = {d["question_id"]: d for d in result["details"]}
    assert by_qid[qid]["user_answer"] == "B"


@pytest.mark.asyncio
async def test_grace_period_submit_accepted(mock_db, questions):
    # 截止后、宽限期内到达的交卷仍按提交答案结算（容忍到点自动交卷的网络延迟）
    now = datetime.utcnow()
    session = {
        "name": "模拟考试",
        "user_id": USER_ID,
        "subject_id": SUBJECT_ID,
        "question_ids": [str(q["_id"]) for q in questions],
        "duration_minutes": 30,
        "start_time": now - timedelta(minutes=30, seconds=SUBMIT_GRACE_SECONDS - 5),
        "end_time": None,
        "answers": {},
        "is_submitted": False,
        "score": None,
        "total_questions": len(questions),
        "correct_count": None
    }
    inserted = await mock_db.exam_sessions.insert_one(session)
    session_id = str(inserted.inserted_id)

    answers = {str(q["_id"]): "A" for q in questions}
    result = await ExamService.submit_exam(session_id, USER_ID, answers)
    assert result["score"] == 100
    # 交卷时间按截止时间计
    assert result["duration_used"] == 30 * 60


@pytest.mark.asyncio
async def test_history_report_remains_readable(mock_db, questions):
    saved = {str(questions[0]["_id"]): "A"}
    session_id = await _make_expired_session(mock_db, questions, answers=saved)

    first = await ExamService.get_result(session_id, USER_ID)
    assert first is not None

    history = await ExamService.get_exam_history(USER_ID)
    assert len(history) == 1
    assert history[0]["id"] == session_id
    assert history[0]["score"] == first["score"]

    # 再次读取历史报告，内容保持一致
    again = await ExamService.get_result(session_id, USER_ID)
    assert again["score"] == first["score"]
    assert again["submitted_at"] == first["submitted_at"]
    assert again["details"] == first["details"]


@pytest.mark.asyncio
async def test_result_not_available_before_submission(questions):
    session = await ExamService.create_exam(
        user_id=USER_ID, name="模拟考试", subject_id=SUBJECT_ID,
        question_count=4, duration_minutes=30
    )
    result = await ExamService.get_result(session["id"], USER_ID)
    assert result is None
