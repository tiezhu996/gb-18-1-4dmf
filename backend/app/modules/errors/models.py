from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel


class ErrorRecord(BaseModel):
    id: str
    question_id: str
    question_content: str
    question_type: str
    subject_id: str
    knowledge_ids: List[str]
    wrong_count: int
    created_at: datetime
    last_wrong_at: datetime
    mastered: bool


class ErrorPracticeStart(BaseModel):
    knowledge_id: Optional[str] = None
    question_count: int = 20
