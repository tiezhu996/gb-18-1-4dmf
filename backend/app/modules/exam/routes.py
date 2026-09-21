from fastapi import APIRouter, Depends, HTTPException, Query
from app.modules.exam.models import ExamConfig, ExamSubmit, ExamSave
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


@router.post("/save")
async def save_answers(
    save_data: ExamSave,
    user: dict = Depends(get_current_user)
):
    """自动保存答案（暂存），到点后拒绝修改并返回已结算状态。"""
    try:
        return await ExamService.save_answers(
            session_id=save_data.session_id,
            user_id=str(user["_id"]),
            answers=save_data.answers
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}")
async def get_exam(
    session_id: str,
    user: dict = Depends(get_current_user)
):
    """获取考试状态用于刷新恢复：未交卷返回题目/剩余时间，已交卷或已到点直接返回已结算标记。"""
    state = await ExamService.get_exam_state(session_id, str(user["_id"]))
    if not state:
        raise HTTPException(status_code=404, detail="考试不存在")
    return state


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
