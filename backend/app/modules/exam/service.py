from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timedelta
import json
from app.core.database import get_db
from app.core.redis import get_redis
from app.modules.questions.service import QuestionService


class ExamService:
    @staticmethod
    async def create_exam(
        user_id: str,
        name: str,
        subject_id: str,
        question_count: int = 30,
        duration_minutes: int = 60
    ) -> dict:
        db = get_db()
        redis = get_redis()

        questions = await QuestionService.get_random_questions(
            subject_id=subject_id,
            count=question_count
        )

        if not questions:
            raise ValueError("没有找到足够的题目")

        question_ids = [str(q["_id"]) for q in questions]
        now = datetime.utcnow()

        session_dict = {
            "name": name,
            "user_id": user_id,
            "subject_id": subject_id,
            "question_ids": question_ids,
            "duration_minutes": duration_minutes,
            "start_time": now,
            "end_time": None,
            "answers": {},
            "is_submitted": False,
            "score": None,
            "total_questions": len(question_ids),
            "correct_count": None
        }

        result = await db.exam_sessions.insert_one(session_dict)
        session_dict["_id"] = str(result.inserted_id)
        session_dict["id"] = str(result.inserted_id)

        if redis:
            key = f"exam:{user_id}:{str(result.inserted_id)}"
            await redis.setex(key, duration_minutes * 60 + 300, json.dumps(session_dict))

        return session_dict

    @staticmethod
    async def get_exam(session_id: str, user_id: str, include_answers: bool = False) -> Optional[dict]:
        db = get_db()
        redis = get_redis()

        if redis and not include_answers:
            key = f"exam:{user_id}:{session_id}"
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)

        if not ObjectId.is_valid(session_id):
            return None
        session = await db.exam_sessions.find_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })

        if session:
            session["id"] = str(session["_id"])
            session["_id"] = str(session["_id"])

        return session

    @staticmethod
    async def get_questions(session_id: str, user_id: str) -> List[dict]:
        session = await ExamService.get_exam(session_id, user_id)
        if not session:
            raise ValueError("考试不存在")

        if session.get("is_submitted"):
            raise ValueError("考试已提交")

        question_ids = session.get("question_ids", [])
        questions = await QuestionService.get_questions_by_ids(question_ids)

        result = []
        for q in questions:
            result.append({
                "id": str(q["_id"]),
                "type": q["type"],
                "content": q["content"],
                "options": q.get("options"),
                "difficulty": q["difficulty"],
                "knowledge_ids": q.get("knowledge_ids", [])
            })
        return result

    @staticmethod
    async def submit_exam(
        session_id: str,
        user_id: str,
        answers: Dict[str, Any]
    ) -> dict:
        db = get_db()
        redis = get_redis()

        session = await ExamService.get_exam(session_id, user_id)
        if not session:
            raise ValueError("考试不存在")

        if session.get("is_submitted"):
            raise ValueError("考试已提交")

        question_ids = session.get("question_ids", [])
        questions = await QuestionService.get_questions_by_ids(question_ids)

        correct_count = 0
        details = []
        for q in questions:
            qid = str(q["_id"])
            user_answer = answers.get(qid)
            correct_answer = q["correct_answer"]
            is_correct = QuestionService.compare_answers(q["type"], user_answer, correct_answer)

            if is_correct:
                correct_count += 1
            else:
                from app.modules.practice.service import PracticeService
                await PracticeService._add_to_errors(user_id, qid)

            details.append({
                "question_id": qid,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "type": q["type"],
                "content": q["content"],
                "options": q.get("options"),
                "explanation": q.get("explanation")
            })

        total = len(questions)
        score = round((correct_count / total) * 100, 1) if total > 0 else 0

        now = datetime.utcnow()
        start_time = session.get("start_time", now)
        duration_used = int((now - start_time).total_seconds())

        update_data = {
            "answers": answers,
            "is_submitted": True,
            "score": score,
            "correct_count": correct_count,
            "end_time": now,
            "duration_used": duration_used,
            "details": details
        }

        await db.exam_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_data}
        )

        if redis:
            key = f"exam:{user_id}:{session_id}"
            await redis.delete(key)

        return {
            "id": session_id,
            "name": session.get("name", "模拟考试"),
            "subject_id": session.get("subject_id"),
            "score": score,
            "total_questions": total,
            "correct_count": correct_count,
            "accuracy": round((correct_count / total) * 100, 1) if total > 0 else 0,
            "duration_used": duration_used,
            "submitted_at": now,
            "details": details
        }

    @staticmethod
    async def get_exam_history(user_id: str, limit: int = 20) -> List[dict]:
        db = get_db()
        cursor = db.exam_sessions.find({
            "user_id": user_id,
            "is_submitted": True
        }).sort("end_time", -1).limit(limit)

        exams = await cursor.to_list(length=limit)
        result = []
        for exam in exams:
            result.append({
                "id": str(exam["_id"]),
                "name": exam.get("name", "模拟考试"),
                "subject_id": exam.get("subject_id"),
                "score": exam.get("score", 0),
                "total_questions": exam.get("total_questions", 0),
                "correct_count": exam.get("correct_count", 0),
                "duration_used": exam.get("duration_used", 0),
                "submitted_at": exam.get("end_time")
            })
        return result
