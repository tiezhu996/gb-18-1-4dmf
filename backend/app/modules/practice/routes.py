from fastapi import APIRouter, Depends, HTTPException
from app.modules.practice.models import PracticeConfig, PracticeSubmit
from app.modules.practice.service import PracticeService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.post("/start")
async def start_practice(
    config: PracticeConfig,
    user: dict = Depends(get_current_user)
):
    try:
        session = await PracticeService.create_session(
            user_id=str(user["_id"]),
            mode=config.mode,
            subject_id=config.subject_id,
            knowledge_ids=config.knowledge_ids,
            question_count=config.question_count,
            difficulty=config.difficulty
        )

        question = await PracticeService.get_current_question(session)
        question_response = {
            "id": str(question["_id"]),
            "type": question["type"],
            "content": question["content"],
            "options": question.get("options"),
            "difficulty": question["difficulty"],
            "knowledge_ids": question.get("knowledge_ids", [])
        } if question else None

        return {
            "session_id": session["id"],
            "current_question": question_response,
            "progress": {
                "current": 0,
                "total": session["total"],
                "correct": 0,
                "accuracy": 0
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit")
async def submit_answer(
    submit_data: PracticeSubmit,
    user: dict = Depends(get_current_user)
):
    try:
        result = await PracticeService.submit_answer(
            session_id=submit_data.session_id,
            user_id=str(user["_id"]),
            question_id=submit_data.question_id,
            user_answer=submit_data.user_answer
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/navigate/{session_id}/{direction}")
async def navigate(
    session_id: str,
    direction: str,
    user: dict = Depends(get_current_user)
):
    try:
        question = await PracticeService.navigate_question(
            session_id=session_id,
            user_id=str(user["_id"]),
            direction=direction
        )
        if question:
            return {
                "id": str(question["_id"]),
                "type": question["type"],
                "content": question["content"],
                "options": question.get("options"),
                "difficulty": question["difficulty"],
                "knowledge_ids": question.get("knowledge_ids", [])
            }
        return None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/progress/{session_id}")
async def get_progress(
    session_id: str,
    user: dict = Depends(get_current_user)
):
    try:
        return await PracticeService.get_session_progress(
            session_id=session_id,
            user_id=str(user["_id"])
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    user: dict = Depends(get_current_user)
):
    session = await PracticeService.get_session(session_id, str(user["_id"]))
    if not session:
        raise HTTPException(status_code=404, detail="练习会话不存在")

    question = await PracticeService.get_current_question(session)
    question_response = {
        "id": str(question["_id"]),
        "type": question["type"],
        "content": question["content"],
        "options": question.get("options"),
        "difficulty": question["difficulty"],
        "knowledge_ids": question.get("knowledge_ids", [])
    } if question else None

    return {
        "session": session,
        "current_question": question_response
    }
