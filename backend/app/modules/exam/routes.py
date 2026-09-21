from fastapi import APIRouter, Depends, HTTPException, Query
from app.modules.exam.models import ExamConfig, ExamSubmit, AnswersSave
from app.modules.exam.service import ExamService, _exam_deadline, _parse_dt
from app.modules.auth.dependencies import get_current_user

from datetime import datetime

router = APIRouter()


def _session_payload(session: dict) -> dict:
    """考试会话的公共信息（含服务端剩余时间，用于刷新后恢复倒计时）。"""
    deadline = _exam_deadline(session)
    remaining = max(int((deadline - datetime.utcnow()).total_seconds()), 0)
    return {
        "session_id": str(session["_id"]),
        "name": session.get("name", "模拟考试"),
        "total_questions": session.get("total_questions"),
        "duration_minutes": session.get("duration_minutes"),
        "start_time": _parse_dt(session.get("start_time")),
        "end_time": deadline,
        "remaining_seconds": remaining,
        "is_submitted": bool(session.get("is_submitted")),
        "answers": session.get("answers") or {}
    }


@router.post("/start")
async def start_exam(
    config: ExamConfig,
    user: dict = Depends(get_current_user)
):
    try:
        session = await ExamService.create_exam(
            user_id=str(user["_id"]),
            name=config.name,
            subject_id=config.subject_id,
            question_count=config.question_count,
            duration_minutes=config.duration_minutes
        )

        questions = await ExamService.get_questions(session["id"], str(user["_id"]))

        return {
            **_session_payload(session),
            "questions": questions
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}")
async def get_exam(
    session_id: str,
    user: dict = Depends(get_current_user)
):
    session = await ExamService.get_exam(session_id, str(user["_id"]))
    if not session:
        raise HTTPException(status_code=404, detail="考试不存在")

    payload = _session_payload(session)
    if session.get("is_submitted"):
        # 已交卷（含到点自动结算）：不再下发题目，前端直接展示结果
        payload["questions"] = []
    else:
        payload["questions"] = await ExamService.get_questions(session_id, str(user["_id"]))
    return payload


@router.put("/{session_id}/answers")
async def save_answers(
    session_id: str,
    data: AnswersSave,
    user: dict = Depends(get_current_user)
):
    try:
        return await ExamService.save_answers(
            session_id=session_id,
            user_id=str(user["_id"]),
            answers=data.answers
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit")
async def submit_exam(
    submit_data: ExamSubmit,
    user: dict = Depends(get_current_user)
):
    try:
        result = await ExamService.submit_exam(
            session_id=submit_data.session_id,
            user_id=str(user["_id"]),
            answers=submit_data.answers
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/result/{session_id}")
async def get_result(
    session_id: str,
    user: dict = Depends(get_current_user)
):
    result = await ExamService.get_result(session_id, str(user["_id"]))
    if not result:
        raise HTTPException(status_code=404, detail="考试结果不存在")
    return result


@router.get("/history/list")
async def get_history(
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    return await ExamService.get_exam_history(str(user["_id"]), limit)
