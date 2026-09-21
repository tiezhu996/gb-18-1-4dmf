from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime
from app.core.database import get_db
from app.modules.questions.models import (
    QuestionCreate, QuestionUpdate, QuestionResponse,
    AnswerCheck, AnswerResult
)


class QuestionService:
    @staticmethod
    def to_response(question: dict) -> dict:
        return {
            **question,
            "id": str(question["_id"]),
            "_id": str(question["_id"])
        }

    @staticmethod
    async def create_question(question_data: QuestionCreate) -> dict:
        db = get_db()
        now = datetime.utcnow()
        question_dict = {
            **question_data.model_dump(),
            "created_at": now,
            "updated_at": now,
            "stats": {
                "answered": 0,
                "correct": 0
            }
        }
        result = await db.questions.insert_one(question_dict)
        question_dict["_id"] = str(result.inserted_id)
        question_dict["id"] = str(result.inserted_id)
        return question_dict

    @staticmethod
    async def get_question_by_id(question_id: str) -> Optional[dict]:
        db = get_db()
        if not ObjectId.is_valid(question_id):
            return None
        question = await db.questions.find_one({"_id": ObjectId(question_id)})
        return question

    @staticmethod
    async def get_questions(
        subject_id: Optional[str] = None,
        knowledge_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        db = get_db()
        query = {}

        if subject_id:
            query["subject_id"] = subject_id
        if knowledge_id:
            query["knowledge_ids"] = {"$in": [knowledge_id]}
        if difficulty:
            query["difficulty"] = difficulty
        if type:
            query["type"] = type

        total = await db.questions.count_documents(query)
        skip = (page - 1) * page_size

        cursor = db.questions.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        questions = await cursor.to_list(length=page_size)

        items = [QuestionService.to_response(q) for q in questions]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    @staticmethod
    async def get_random_questions(
        subject_id: str,
        knowledge_ids: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        count: int = 20
    ) -> List[dict]:
        db = get_db()
        query = {"subject_id": subject_id}

        if knowledge_ids:
            query["knowledge_ids"] = {"$in": knowledge_ids}
        if difficulty:
            query["difficulty"] = difficulty

        pipeline = [
            {"$match": query},
            {"$sample": {"size": count}}
        ]
        questions = await db.questions.aggregate(pipeline).to_list(length=count)
        return questions

    @staticmethod
    async def get_questions_by_ids(question_ids: List[str]) -> List[dict]:
        db = get_db()
        object_ids = [ObjectId(qid) for qid in question_ids if ObjectId.is_valid(qid)]
        cursor = db.questions.find({"_id": {"$in": object_ids}})
        questions = await cursor.to_list(length=None)
        question_map = {str(q["_id"]): q for q in questions}
        return [question_map[qid] for qid in question_ids if qid in question_map]

    @staticmethod
    async def check_answer(
        question_id: str,
        user_answer: Any,
        user_id: str
    ) -> AnswerResult:
        db = get_db()
        question = await QuestionService.get_question_by_id(question_id)
        if not question:
            raise ValueError("题目不存在")

        correct_answer = question["correct_answer"]
        is_correct = QuestionService.compare_answers(question["type"], user_answer, correct_answer)

        update_data = {"$inc": {"stats.answered": 1}}
        if is_correct:
            update_data["$inc"]["stats.correct"] = 1

        await db.questions.update_one({"_id": ObjectId(question_id)}, update_data)

        return AnswerResult(
            question_id=question_id,
            is_correct=is_correct,
            correct_answer=correct_answer,
            explanation=question.get("explanation")
        )

    @staticmethod
    def compare_answers(q_type: str, user_answer: Any, correct_answer: Any) -> bool:
        if q_type in ["single_choice", "true_false"]:
            return str(user_answer).upper() == str(correct_answer).upper()
        elif q_type == "multiple_choice":
            if isinstance(user_answer, list):
                user_set = set(str(a).upper() for a in user_answer)
            else:
                user_set = {str(user_answer).upper()}
            correct_set = set(str(a).upper() for a in correct_answer)
            return user_set == correct_set
        elif q_type == "fill_blank":
            return str(user_answer).strip() == str(correct_answer).strip()
        return False

    @staticmethod
    async def update_question(question_id: str, update_data: QuestionUpdate) -> Optional[dict]:
        db = get_db()
        if not ObjectId.is_valid(question_id):
            return None

        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if update_dict:
            update_dict["updated_at"] = datetime.utcnow()
            await db.questions.update_one(
                {"_id": ObjectId(question_id)},
                {"$set": update_dict}
            )

        return await QuestionService.get_question_by_id(question_id)

    @staticmethod
    async def delete_question(question_id: str) -> bool:
        db = get_db()
        if not ObjectId.is_valid(question_id):
            return False
        result = await db.questions.delete_one({"_id": ObjectId(question_id)})
        return result.deleted_count > 0
