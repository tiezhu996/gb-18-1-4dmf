from fastapi import APIRouter, Depends, HTTPException, Query
from app.modules.exam.models import ExamConfig, ExamSubmit
from app.modules.exam.service import ExamService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


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
            "session_id": session["id"],
            "name": session["name"],
            "total_questions": session["total_questions"],
            "duration_minutes": session["duration_minutes"],
            "start_time": session["start_time"],
            "questions": questions
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}")
async def get_exam(
    session_id: str,
    user: dict = Depends(get_current_user)
):
    try:
        questions = await ExamService.get_questions(session_id, str(user["_id"]))
        session = await ExamService.get_exam(session_id, str(user["_id"]))

        return {
            "session_id": session_id,
            "name": session.get("name", "模拟考试"),
            "total_questions": session.get("total_questions"),
            "duration_minutes": session.get("duration_minutes"),
            "start_time": session.get("start_time"),
            "questions": questions
        }
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
    session = await ExamService.get_exam(session_id, str(user["_id"]), include_answers=True)
    if not session or not session.get("is_submitted"):
        raise HTTPException(status_code=404, detail="考试结果不存在")

    return {
        "id": session_id,
        "name": session.get("name", "模拟考试"),
        "subject_id": session.get("subject_id"),
        "score": session.get("score", 0),
        "total_questions": session.get("total_questions", 0),
        "correct_count": session.get("correct_count", 0),
        "accuracy": session.get("score", 0),
        "duration_used": session.get("duration_used", 0),
        "submitted_at": session.get("end_time"),
        "details": session.get("details", [])
    }


@router.get("/history/list")
async def get_history(
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    return await ExamService.get_exam_history(str(user["_id"]), limit)
