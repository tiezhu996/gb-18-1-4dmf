from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class LearningOverview(BaseModel):
    total_practiced: int
    total_correct: int
    accuracy: float
    total_exams: int
    avg_exam_score: float
    weak_knowledge: List[Dict[str, Any]]


class KnowledgeMastery(BaseModel):
    knowledge_id: str
    knowledge_name: str
    total_answered: int
    correct_count: int
    mastery_rate: float


class AccuracyTrend(BaseModel):
    date: str
    accuracy: float
    total: int
    correct: int
