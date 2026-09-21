from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timedelta
from pymongo import ReturnDocument
import json
from app.core.database import get_db
from app.core.redis import get_redis
from app.modules.questions.service import QuestionService

# 交卷宽限期（秒）：截止后短暂时间内到达的交卷/保存请求仍被接受，
# 用于容忍前端倒计时到点自动交卷的网络延迟；超过宽限期则按已保存答案结算。
SUBMIT_GRACE_SECONDS = 30


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _exam_deadline(session: dict) -> datetime:
    start_time = _parse_dt(session.get("start_time")) or datetime.utcnow()
    duration_minutes = session.get("duration_minutes", 60)
    return start_time + timedelta(minutes=duration_minutes)


def _build_result(session: dict) -> dict:
    """从已结算的考试会话构建成绩报告，保证各接口返回一致。"""
    score = session.get("score") or 0
    return {
        "id": str(session["_id"]),
        "name": session.get("name", "模拟考试"),
        "subject_id": session.get("subject_id"),
        "score": score,
        "total_questions": session.get("total_questions", 0),
        "correct_count": session.get("correct_count", 0),
        "accuracy": score,
        "duration_used": session.get("duration_used", 0),
        "submitted_at": _parse_dt(session.get("end_time")),
        "details": session.get("details", [])
    }


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
            await redis.setex(
                key,
                duration_minutes * 60 + 300,
                json.dumps(session_dict, default=str)
            )

        return session_dict

    @staticmethod
    async def _get_session_doc(session_id: str, user_id: str) -> Optional[dict]:
        """从数据库读取最新的考试会话（绕过缓存，保证状态准确）。"""
        db = get_db()
        if not ObjectId.is_valid(session_id):
            return None
        return await db.exam_sessions.find_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })

    @staticmethod
    async def get_exam(session_id: str, user_id: str, include_answers: bool = False) -> Optional[dict]:
        db = get_db()
        redis = get_redis()

        session = None
        if redis and not include_answers:
            key = f"exam:{user_id}:{session_id}"
            cached = await redis.get(key)
            if cached:
                session = json.loads(cached)

        if session is None:
            session = await ExamService._get_session_doc(session_id, user_id)

        if not session:
            return None

        # 到达截止时间且未交卷：按已保存答案自动结算（只发生一次）
        if not session.get("is_submitted") and datetime.utcnow() >= _exam_deadline(session):
            session = await ExamService._settle_session(session, None)

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
    async def save_answers(session_id: str, user_id: str, answers: Dict[str, Any]) -> dict:
        """保存答题进度。已交卷或已到截止时间的考试不再接受修改。"""
        db = get_db()
        redis = get_redis()

        session = await ExamService._get_session_doc(session_id, user_id)
        if not session:
            raise ValueError("考试不存在")

        now = datetime.utcnow()
        deadline = _exam_deadline(session)

        if session.get("is_submitted") or now > deadline + timedelta(seconds=SUBMIT_GRACE_SECONDS):
            # 已结算或已到点：触发/回读自动结算，不再保存新答案
            session = await ExamService.get_exam(session_id, user_id)
            return {
                "saved": False,
                "is_submitted": True,
                "remaining_seconds": 0
            }

        # 仅接受本场考试的题目，按题号逐字段更新，避免并发保存互相覆盖
        valid_qids = set(session.get("question_ids", []))
        updates = {
            f"answers.{qid}": value
            for qid, value in (answers or {}).items()
            if qid in valid_qids
        }
        if updates:
            await db.exam_sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": updates}
            )

        if redis:
            merged = dict(session.get("answers") or {})
            merged.update(answers or {})
            session["answers"] = merged
            session["id"] = str(session["_id"])
            session["_id"] = str(session["_id"])
            key = f"exam:{user_id}:{session_id}"
            ttl = max(int((deadline - now).total_seconds()) + 300, 300)
            await redis.setex(key, ttl, json.dumps(session, default=str))

        remaining = max(int((deadline - now).total_seconds()), 0)
        return {
            "saved": True,
            "is_submitted": False,
            "remaining_seconds": remaining
        }

    @staticmethod
    async def _settle_session(session: dict, answers: Optional[Dict[str, Any]]) -> dict:
        """
        结算考试：批改并原子写入结果。
        结算只会成功写入一次；并发或重复结算时回读首次写入的报告。
        answers 为 None 时使用会话中已保存的答案（自动结算）。
        """
        db = get_db()
        redis = get_redis()

        session_id = str(session["_id"])
        user_id = session.get("user_id")

        final_answers = answers if answers is not None else (session.get("answers") or {})

        question_ids = session.get("question_ids", [])
        questions = await QuestionService.get_questions_by_ids(question_ids)

        correct_count = 0
        details = []
        wrong_question_ids = []
        for q in questions:
            qid = str(q["_id"])
            user_answer = final_answers.get(qid)
            correct_answer = q["correct_answer"]
            is_correct = QuestionService.compare_answers(q["type"], user_answer, correct_answer)

            if is_correct:
                correct_count += 1
            else:
                wrong_question_ids.append(qid)

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
        start_time = _parse_dt(session.get("start_time")) or now
        deadline = _exam_deadline(session)
        # 交卷时间不晚于截止时间：超时自动结算按截止时间计
        end_time = min(now, deadline)
        duration_used = max(int((end_time - start_time).total_seconds()), 0)

        update_data = {
            "answers": final_answers,
            "is_submitted": True,
            "score": score,
            "correct_count": correct_count,
            "end_time": end_time,
            "duration_used": duration_used,
            "details": details
        }

        updated = await db.exam_sessions.find_one_and_update(
            {"_id": ObjectId(session_id), "is_submitted": False},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )

        if updated is None:
            # 已被其他请求结算：回读首次报告
            updated = await db.exam_sessions.find_one({"_id": ObjectId(session_id)})
        else:
            # 只有真正完成结算的请求才记录错题，避免重复计数
            from app.modules.practice.service import PracticeService
            for qid in wrong_question_ids:
                await PracticeService._add_to_errors(user_id, qid)

        if redis:
            key = f"exam:{user_id}:{session_id}"
            await redis.delete(key)

        return updated

    @staticmethod
    async def submit_exam(
        session_id: str,
        user_id: str,
        answers: Dict[str, Any]
    ) -> dict:
        session = await ExamService._get_session_doc(session_id, user_id)
        if not session:
            raise ValueError("考试不存在")

        # 已交卷：重复交卷直接回读首次报告
        if session.get("is_submitted"):
            return _build_result(session)

        now = datetime.utcnow()
        deadline = _exam_deadline(session)

        if now <= deadline + timedelta(seconds=SUBMIT_GRACE_SECONDS):
            # 截止前（含宽限期内）交卷：按提交的答案结算
            settled = await ExamService._settle_session(session, answers)
        else:
            # 超过截止时间：按已保存答案自动结算，迟到答案不生效
            settled = await ExamService._settle_session(session, None)

        return _build_result(settled)

    @staticmethod
    async def get_result(session_id: str, user_id: str) -> Optional[dict]:
        """读取成绩报告；到点未交卷的考试在此触发自动结算。"""
        session = await ExamService.get_exam(session_id, user_id, include_answers=True)
        if not session or not session.get("is_submitted"):
            return None
        return _build_result(session)

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
