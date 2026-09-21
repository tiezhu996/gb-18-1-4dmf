from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime
from app.core.database import get_db
from app.modules.questions.service import QuestionService


class ErrorService:
    @staticmethod
    async def get_errors(
        user_id: str,
        subject_id: Optional[str] = None,
        knowledge_id: Optional[str] = None,
        mastered: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        db = get_db()
        query = {
            "user_id": user_id,
            "mastered": mastered
        }

        if subject_id:
            query["subject_id"] = subject_id
        if knowledge_id:
            query["knowledge_ids"] = {"$in": [knowledge_id]}

        total = await db.errors.count_documents(query)
        skip = (page - 1) * page_size

        cursor = db.errors.find(query).sort("last_wrong_at", -1).skip(skip).limit(page_size)
        errors = await cursor.to_list(length=page_size)

        question_ids = [e["question_id"] for e in errors]
        questions = await QuestionService.get_questions_by_ids(question_ids)
        question_map = {str(q["_id"]): q for q in questions}

        result = []
        for error in errors:
            q = question_map.get(error["question_id"])
            if q:
                result.append({
                    "id": str(error["_id"]),
                    "question_id": error["question_id"],
                    "question": {
                        "id": str(q["_id"]),
                        "type": q["type"],
                        "content": q["content"],
                        "options": q.get("options"),
                        "correct_answer": q["correct_answer"],
                        "explanation": q.get("explanation"),
                        "difficulty": q["difficulty"],
                        "knowledge_ids": q.get("knowledge_ids", [])
                    },
                    "wrong_count": error.get("wrong_count", 1),
                    "created_at": error.get("created_at"),
                    "last_wrong_at": error.get("last_wrong_at"),
                    "mastered": error.get("mastered", False)
                })

        return {
            "items": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    @staticmethod
    async def mark_mastered(user_id: str, question_id: str) -> bool:
        db = get_db()
        result = await db.errors.update_one(
            {"user_id": user_id, "question_id": question_id},
            {"$set": {"mastered": True}}
        )
        return result.modified_count > 0

    @staticmethod
    async def unmark_mastered(user_id: str, question_id: str) -> bool:
        db = get_db()
        result = await db.errors.update_one(
            {"user_id": user_id, "question_id": question_id},
            {"$set": {"mastered": False}}
        )
        return result.modified_count > 0

    @staticmethod
    async def remove_error(user_id: str, question_id: str) -> bool:
        db = get_db()
        result = await db.errors.delete_one({
            "user_id": user_id,
            "question_id": question_id
        })
        return result.deleted_count > 0

    @staticmethod
    async def get_errors_for_practice(
        user_id: str,
        knowledge_id: Optional[str] = None,
        count: int = 20
    ) -> List[str]:
        db = get_db()
        query = {
            "user_id": user_id,
            "mastered": False
        }
        if knowledge_id:
            query["knowledge_ids"] = {"$in": [knowledge_id]}

        cursor = db.errors.find(query).sort("wrong_count", -1).limit(count)
        errors = await cursor.to_list(length=count)
        return [e["question_id"] for e in errors]

    @staticmethod
    async def get_error_stats(user_id: str) -> Dict[str, Any]:
        db = get_db()

        total_errors = await db.errors.count_documents({
            "user_id": user_id,
            "mastered": False
        })

        mastered_count = await db.errors.count_documents({
            "user_id": user_id,
            "mastered": True
        })

        pipeline = [
            {"$match": {"user_id": user_id, "mastered": False}},
            {"$unwind": "$knowledge_ids"},
            {"$group": {
                "_id": "$knowledge_ids",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]

        knowledge_stats = await db.errors.aggregate(pipeline).to_list(length=10)

        return {
            "total_errors": total_errors,
            "mastered_count": mastered_count,
            "knowledge_stats": knowledge_stats
        }
