from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime
import json
from app.core.database import get_db
from app.core.redis import get_redis
from app.modules.questions.service import QuestionService


class PracticeService:
    @staticmethod
    async def create_session(
        user_id: str,
        mode: str,
        subject_id: str,
        knowledge_ids: Optional[List[str]] = None,
        question_count: int = 20,
        difficulty: Optional[str] = None
    ) -> dict:
        db = get_db()
        redis = get_redis()

        if mode == "random":
            questions = await QuestionService.get_random_questions(
                subject_id=subject_id,
                knowledge_ids=knowledge_ids,
                difficulty=difficulty,
                count=question_count
            )
        else:
            query = {"subject_id": subject_id}
            if knowledge_ids:
                query["knowledge_ids"] = {"$in": knowledge_ids}
            if difficulty:
                query["difficulty"] = difficulty
            cursor = db.questions.find(query).limit(question_count)
            questions = await cursor.to_list(length=question_count)

        if not questions:
            raise ValueError("没有找到符合条件的题目")

        question_ids = [str(q["_id"]) for q in questions]
        session_dict = {
            "user_id": user_id,
            "mode": mode,
            "subject_id": subject_id,
            "knowledge_ids": knowledge_ids,
            "question_ids": question_ids,
            "current_index": 0,
            "answers": {},
            "total": len(question_ids),
            "correct_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await db.practice_sessions.insert_one(session_dict)
        session_dict["_id"] = str(result.inserted_id)
        session_dict["id"] = str(result.inserted_id)

        if redis:
            key = f"practice:{user_id}:{str(result.inserted_id)}"
            await redis.setex(key, 3600 * 24, json.dumps(session_dict))

        return session_dict

    @staticmethod
    async def get_session(session_id: str, user_id: str) -> Optional[dict]:
        db = get_db()
        redis = get_redis()

        if redis:
            key = f"practice:{user_id}:{session_id}"
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)

        if not ObjectId.is_valid(session_id):
            return None
        session = await db.practice_sessions.find_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })

        if session:
            session["id"] = str(session["_id"])
            session["_id"] = str(session["_id"])
            if redis:
                key = f"practice:{user_id}:{session_id}"
                await redis.setex(key, 3600 * 24, json.dumps(session))

        return session

    @staticmethod
    async def get_current_question(session: dict) -> Optional[dict]:
        current_index = session.get("current_index", 0)
        question_ids = session.get("question_ids", [])
        if 0 <= current_index < len(question_ids):
            return await QuestionService.get_question_by_id(question_ids[current_index])
        return None

    @staticmethod
    async def submit_answer(
        session_id: str,
        user_id: str,
        question_id: str,
        user_answer: Any
    ) -> Dict[str, Any]:
        db = get_db()
        redis = get_redis()

        session = await PracticeService.get_session(session_id, user_id)
        if not session:
            raise ValueError("练习会话不存在")

        result = await QuestionService.check_answer(question_id, user_answer, user_id)

        current_index = session.get("current_index", 0)
        question_ids = session.get("question_ids", [])

        is_new_answer = question_id not in session.get("answers", {})
        new_answers = session.get("answers", {}).copy()
        new_answers[question_id] = {
            "user_answer": user_answer,
            "is_correct": result.is_correct,
            "submitted_at": datetime.utcnow().isoformat()
        }

        new_correct_count = session.get("correct_count", 0)
        if result.is_correct and is_new_answer:
            new_correct_count += 1

        update_data = {
            "answers": new_answers,
            "correct_count": new_correct_count,
            "current_index": min(current_index + 1, len(question_ids)),
            "updated_at": datetime.utcnow()
        }

        await db.practice_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_data}
        )

        if not result.is_correct:
            await PracticeService._add_to_errors(user_id, question_id)

        session.update(update_data)
        if redis:
            key = f"practice:{user_id}:{session_id}"
            await redis.setex(key, 3600 * 24, json.dumps(session))

        progress = {
            "current": session["current_index"],
            "total": session["total"],
            "correct": new_correct_count,
            "accuracy": round(new_correct_count / session["current_index"] * 100, 1) if session["current_index"] > 0 else 0
        }

        return {
            "question_id": question_id,
            "is_correct": result.is_correct,
            "correct_answer": result.correct_answer,
            "explanation": result.explanation,
            "progress": progress,
            "is_finished": session["current_index"] >= session["total"]
        }

    @staticmethod
    async def _add_to_errors(user_id: str, question_id: str):
        db = get_db()
        question = await QuestionService.get_question_by_id(question_id)
        if not question:
            return

        existing = await db.errors.find_one({
            "user_id": user_id,
            "question_id": question_id
        })

        if existing:
            await db.errors.update_one(
                {"_id": existing["_id"]},
                {
                    "$inc": {"wrong_count": 1},
                    "$set": {"last_wrong_at": datetime.utcnow()}
                }
            )
        else:
            await db.errors.insert_one({
                "user_id": user_id,
                "question_id": question_id,
                "subject_id": question.get("subject_id"),
                "knowledge_ids": question.get("knowledge_ids", []),
                "wrong_count": 1,
                "created_at": datetime.utcnow(),
                "last_wrong_at": datetime.utcnow(),
                "mastered": False
            })

    @staticmethod
    async def navigate_question(
        session_id: str,
        user_id: str,
        direction: str
    ) -> Optional[dict]:
        db = get_db()
        redis = get_redis()

        session = await PracticeService.get_session(session_id, user_id)
        if not session:
            raise ValueError("练习会话不存在")

        question_ids = session.get("question_ids", [])
        current_index = session.get("current_index", 0)

        if direction == "prev":
            new_index = max(0, current_index - 1)
        elif direction == "next":
            new_index = min(len(question_ids) - 1, current_index + 1)
        else:
            new_index = current_index

        await db.practice_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"current_index": new_index}}
        )

        session["current_index"] = new_index
        if redis:
            key = f"practice:{user_id}:{session_id}"
            await redis.setex(key, 3600 * 24, json.dumps(session))

        if 0 <= new_index < len(question_ids):
            return await QuestionService.get_question_by_id(question_ids[new_index])
        return None

    @staticmethod
    async def get_session_progress(session_id: str, user_id: str) -> dict:
        session = await PracticeService.get_session(session_id, user_id)
        if not session:
            raise ValueError("练习会话不存在")

        answers = session.get("answers", {})
        correct_count = sum(1 for a in answers.values() if a.get("is_correct"))

        return {
            "current": session.get("current_index", 0),
            "total": session.get("total", 0),
            "correct": correct_count,
            "accuracy": round(correct_count / len(answers) * 100, 1) if answers else 0,
            "answers": answers
        }
