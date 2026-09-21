from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class KnowledgeNodeBase(BaseModel):
    name: str
    level: int
    parent_id: Optional[str] = None
    subject_id: str
    order: int = 0
    description: Optional[str] = None


class KnowledgeNodeCreate(KnowledgeNodeBase):
    pass


class KnowledgeNodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class KnowledgeNodeResponse(BaseModel):
    id: str
    name: str
    level: int
    parent_id: Optional[str]
    subject_id: str
    order: int
    description: Optional[str]
    question_count: int = 0
    children: List["KnowledgeNodeResponse"] = []

    class Config:
        from_attributes = True


class SubjectBase(BaseModel):
    name: str
    icon: Optional[str] = None
    description: Optional[str] = None
    color: str = "#1890ff"


class SubjectCreate(SubjectBase):
    pass


class SubjectResponse(SubjectBase):
    id: str
    created_at: datetime
    question_count: int = 0
    chapter_count: int = 0

    class Config:
        from_attributes = True


KnowledgeNodeResponse.model_rebuild()
