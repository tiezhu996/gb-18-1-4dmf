from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.modules.analysis.service import AnalysisService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/overview")
async def get_overview(user: dict = Depends(get_current_user)):
    return await AnalysisService.get_learning_overview(str(user["_id"]))


@router.get("/accuracy-trend")
async def get_accuracy_trend(
    days: int = Query(7, ge=1, le=30),
    user: dict = Depends(get_current_user)
):
    return await AnalysisService.get_accuracy_trend(str(user["_id"]), days)


@router.get("/knowledge-mastery/{subject_id}")
async def get_knowledge_mastery(
    subject_id: str,
    user: dict = Depends(get_current_user)
):
    return await AnalysisService.get_knowledge_mastery(str(user["_id"]), subject_id)


@router.get("/recommendations")
async def get_recommendations(user: dict = Depends(get_current_user)):
    return await AnalysisService.get_recommendations(str(user["_id"]))
