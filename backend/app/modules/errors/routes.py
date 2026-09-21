from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.modules.errors.service import ErrorService
from app.modules.errors.models import ErrorPracticeStart
from app.modules.practice.service import PracticeService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/list")
async def list_errors(
    subject_id: Optional[str] = Query(None),
    knowledge_id: Optional[str] = Query(None),
    mastered: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    return await ErrorService.get_errors(
        user_id=str(user["_id"]),
        subject_id=subject_id,
        knowledge_id=knowledge_id,
        mastered=mastered,
        page=page,
        page_size=page_size
    )


@router.post("/mark-mastered/{question_id}")
async def mark_mastered(
    question_id: str,
    user: dict = Depends(get_current_user)
):
    success = await ErrorService.mark_mastered(str(user["_id"]), question_id)
    return {"success": success}


@router.post("/unmark-mastered/{question_id}")
async def unmark_mastered(
    question_id: str,
    user: dict = Depends(get_current_user)
):
    success = await ErrorService.unmark_mastered(str(user["_id"]), question_id)
    return {"success": success}


@router.delete("/{question_id}")
async def remove_error(
    question_id: str,
    user: dict = Depends(get_current_user)
):
    success = await ErrorService.remove_error(str(user["_id"]), question_id)
    return {"success": success}


@router.post("/start-practice")
async def start_error_practice(
    config: ErrorPracticeStart,
    user: dict = Depends(get_current_user)
):
    error_ids = await ErrorService.get_errors_for_practice(
        user_id=str(user["_id"]),
        knowledge_id=config.knowledge_id,
        count=config.question_count
    )

    if not error_ids:
        return {"message": "没有错题需要练习"}

    session = await PracticeService.create_session(
        user_id=str(user["_id"]),
        mode="error_practice",
        subject_id="error_review",
        question_count=len(error_ids)
    )

    from bson import ObjectId
    from app.core.database import get_db
    db = get_db()
    await db.practice_sessions.update_one(
        {"_id": ObjectId(session["id"])},
        {"$set": {"question_ids": error_ids}}
    )
    session["question_ids"] = error_ids
    session["total"] = len(error_ids)

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


@router.get("/stats")
async def get_error_stats(user: dict = Depends(get_current_user)):
    return await ErrorService.get_error_stats(str(user["_id"]))
