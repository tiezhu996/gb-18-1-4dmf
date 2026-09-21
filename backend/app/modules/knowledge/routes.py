from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.modules.knowledge.models import (
    SubjectCreate, SubjectResponse, KnowledgeNodeCreate,
    KnowledgeNodeResponse
)
from app.modules.knowledge.service import KnowledgeService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/subjects", response_model=List[SubjectResponse])
async def list_subjects(user: dict = Depends(get_current_user)):
    return await KnowledgeService.get_subjects()


@router.post("/subjects", response_model=SubjectResponse)
async def create_subject(
    subject_data: SubjectCreate,
    user: dict = Depends(get_current_user)
):
    return await KnowledgeService.create_subject(subject_data)


@router.get("/tree/{subject_id}", response_model=List[KnowledgeNodeResponse])
async def get_knowledge_tree(
    subject_id: str,
    user: dict = Depends(get_current_user)
):
    return await KnowledgeService.get_knowledge_tree(subject_id)


@router.post("/nodes", response_model=KnowledgeNodeResponse)
async def create_knowledge_node(
    node_data: KnowledgeNodeCreate,
    user: dict = Depends(get_current_user)
):
    return await KnowledgeService.create_knowledge_node(node_data)


@router.get("/search/{subject_id}", response_model=List[KnowledgeNodeResponse])
async def search_knowledge(
    subject_id: str,
    keyword: str = Query(..., min_length=1),
    user: dict = Depends(get_current_user)
):
    return await KnowledgeService.search_knowledge(subject_id, keyword)


@router.get("/node/{node_id}", response_model=KnowledgeNodeResponse)
async def get_node(
    node_id: str,
    user: dict = Depends(get_current_user)
):
    node = await KnowledgeService.get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="知识点不存在")
    return node
