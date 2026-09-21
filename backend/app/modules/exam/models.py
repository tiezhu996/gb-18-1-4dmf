from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ExamConfig(BaseModel):
    name: str = "模拟考试"
    subject_id: str
    question_count: int = 30
    duration_minutes: int = 60


class ExamSession(BaseModel):
    id: str
    name: str
    user_id: str
    subject_id: str
    question_ids: List[str]
    duration_minutes: int
    start_time: datetime
    end_time: Optional[datetime]
    answers: Dict[str, Any]
    is_submitted: bool
    score: Optional[float]
    total_questions: int
    correct_count: Optional[int]


class ExamSubmit(BaseModel):
    session_id: str
    answers: Dict[str, Any]


class ExamSave(BaseModel):
    session_id: str
    answers: Dict[str, Any]


class ExamResult(BaseModel):
    id: str
    name: str
    subject_id: str
    score: float
    total_questions: int
    correct_count: int
    accuracy: float
    duration_used: int
    submitted_at: datetime
    details: Optional[List[Dict[str, Any]]] = None
