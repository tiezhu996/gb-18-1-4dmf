from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import Optional, List
import pandas as pd
from io import BytesIO
from app.modules.questions.models import (
    QuestionCreate, QuestionResponse, QuestionListResponse,
    AnswerCheck, AnswerResult, QuestionUpdate
)
from app.modules.questions.service import QuestionService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.get("", response_model=QuestionListResponse)
async def list_questions(
    subject_id: Optional[str] = Query(None),
    knowledge_id: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    return await QuestionService.get_questions(
        subject_id=subject_id,
        knowledge_id=knowledge_id,
        difficulty=difficulty,
        type=type,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=QuestionResponse)
async def create_question(
    question_data: QuestionCreate,
    user: dict = Depends(get_current_user)
):
    return await QuestionService.create_question(question_data)


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: str,
    user: dict = Depends(get_current_user)
):
    question = await QuestionService.get_question_by_id(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return QuestionService.to_response(question)


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    update_data: QuestionUpdate,
    user: dict = Depends(get_current_user)
):
    question = await QuestionService.update_question(question_id, update_data)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return QuestionService.to_response(question)


@router.delete("/{question_id}")
async def delete_question(
    question_id: str,
    user: dict = Depends(get_current_user)
):
    success = await QuestionService.delete_question(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {"success": True}


@router.post("/check-answer", response_model=AnswerResult)
async def check_answer(
    check_data: AnswerCheck,
    user: dict = Depends(get_current_user)
):
    try:
        return await QuestionService.check_answer(
            check_data.question_id,
            check_data.user_answer,
            str(user["_id"])
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import")
async def import_questions(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    try:
        contents = await file.read()
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(BytesIO(contents))
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="只支持 Excel 或 CSV 格式")

        imported_count = 0
        for _, row in df.iterrows():
            try:
                question_data = QuestionCreate(
                    type=str(row.get('type', 'single_choice')),
                    content=str(row.get('content', '')),
                    subject_id=str(row.get('subject_id', '')),
                    knowledge_ids=str(row.get('knowledge_ids', '')).split(','),
                    difficulty=str(row.get('difficulty', 'medium')),
                    correct_answer=row.get('correct_answer'),
                    explanation=str(row.get('explanation', '')) if row.get('explanation') else None
                )
                await QuestionService.create_question(question_data)
                imported_count += 1
            except Exception:
                continue

        return {"success": True, "imported": imported_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
