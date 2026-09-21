from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    key: str
    content: str


class QuestionBase(BaseModel):
    type: str
    content: str
    options: Optional[List[QuestionOption]] = None
    correct_answer: Any
    explanation: Optional[str] = None
    subject_id: str
    knowledge_ids: List[str]
    difficulty: str = "medium"
    tags: List[str] = []


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    type: Optional[str] = None
    content: Optional[str] = None
    options: Optional[List[QuestionOption]] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    knowledge_ids: Optional[List[str]] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None


class QuestionResponse(BaseModel):
    id: str
    type: str
    content: str
    options: Optional[List[QuestionOption]] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    subject_id: str
    knowledge_ids: List[str]
    difficulty: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionForPractice(BaseModel):
    id: str
    type: str
    content: str
    options: Optional[List[QuestionOption]] = None
    subject_id: str
    knowledge_ids: List[str]
    difficulty: str

    class Config:
        from_attributes = True


class AnswerCheck(BaseModel):
    question_id: str
    user_answer: Any


class AnswerResult(BaseModel):
    question_id: str
    is_correct: bool
    correct_answer: Any
    explanation: Optional[str] = None


class QuestionListResponse(BaseModel):
    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int
