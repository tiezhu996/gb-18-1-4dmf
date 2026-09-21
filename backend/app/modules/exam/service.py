from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timedelta
import asyncio
from app.core.database import get_db
from app.core.redis import get_redis
from app.modules.questions.service import QuestionService


# 结算锁过期时间（秒），防止结算进程异常退出后考试永久挂起
SETTLE_LOCK_STALE_SECONDS = 30


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

        return session_dict

    @staticmethod
    async def get_exam(session_id: str, user_id: str, include_answers: bool = False) -> Optional[dict]:
        db = get_db()

        if not ObjectId.is_valid(session_id):
            return None
        # 统一以数据库为准：答案/结算状态必须强一致，避免 Redis 缓存里的 datetime 字符串与状态滞后
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

        return await ExamService._build_question_payload(session)

    # ------------------------------------------------------------------
    # 状态查询 / 答案暂存（供刷新恢复与到点自动结算使用）
    # ------------------------------------------------------------------

    @staticmethod
    async def get_exam_state(session_id: str, user_id: str) -> Optional[dict]:
        """返回考试当前状态；已到截止时间但未结算的会在此刻惰性自动结算。"""
        session = await ExamService._load_session(session_id, user_id)
        if not session:
            return None

        if not session.get("is_submitted") and ExamService._is_due(session):
            await ExamService._claim_and_settle(
                session, session.get("answers") or {}, datetime.utcnow()
            )
            session = await ExamService._wait_until_submitted(session)
            if not session:
                return None

        if session.get("is_submitted"):
            return {
                "session_id": str(session["_id"]),
                "name": session.get("name", "模拟考试"),
                "total_questions": session.get("total_questions", 0),
                "duration_minutes": session.get("duration_minutes", 0),
                "is_submitted": True,
                "remaining_seconds": 0
            }

        now = datetime.utcnow()
        deadline = ExamService._deadline(session)
        remaining_seconds = max(0, int((deadline - now).total_seconds())) if deadline else 0

        return {
            "session_id": str(session["_id"]),
            "name": session.get("name", "模拟考试"),
            "total_questions": session.get("total_questions", 0),
            "duration_minutes": session.get("duration_minutes", 0),
            "start_time": session.get("start_time"),
            "remaining_seconds": remaining_seconds,
            "is_submitted": False,
            "saved_answers": session.get("answers") or {},
            "questions": await ExamService._build_question_payload(session)
        }

    @staticmethod
    async def save_answers(
        session_id: str,
        user_id: str,
        answers: Dict[str, Any]
    ) -> dict:
        """暂存（自动保存）答案。已交卷或已到点则触发/确认结算，拒绝继续修改。"""
        db = get_db()

        # 直接读数据库（含真实 datetime），保证到点判断和答案状态强一致
        session = await ExamService._load_session(session_id, user_id)
        if not session:
            raise ValueError("考试不存在")

        if session.get("is_submitted"):
            return {"is_submitted": True, "remaining_seconds": 0}

        now = datetime.utcnow()
        if ExamService._is_due(session, now):
            # 到点后答案立即冻结，按已保存答案自动结算
            await ExamService._claim_and_settle(
                session, session.get("answers") or {}, now
            )
            return {"is_submitted": True, "remaining_seconds": 0}

        valid_ids = set(session.get("question_ids") or [])
        saved = dict(session.get("answers") or {})
        for qid, value in (answers or {}).items():
            if qid in valid_ids:
                saved[qid] = value

        await db.exam_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"answers": saved}}
        )

        deadline = ExamService._deadline(session)
        remaining_seconds = max(0, int((deadline - now).total_seconds())) if deadline else 0
        return {"is_submitted": False, "remaining_seconds": remaining_seconds}

    # ------------------------------------------------------------------
    # 交卷 / 结算
    # ------------------------------------------------------------------

    @staticmethod
    async def submit_exam(
        session_id: str,
        user_id: str,
        answers: Dict[str, Any]
    ) -> dict:
        """提交试卷。结算全局只发生一次：重复或并发交卷一律回读首次报告。"""
        session = await ExamService._load_session(session_id, user_id)
        if not session:
            raise ValueError("考试不存在")

        if session.get("is_submitted"):
            # 重复交卷：直接回读首次报告
            return ExamService._build_result(session)

        now = datetime.utcnow()

        if ExamService._is_due(session, now):
            # 到点自动结算：忽略本次上送内容，严格按服务端已保存的答案结算
            await ExamService._claim_and_settle(
                session, session.get("answers") or {}, now
            )
        else:
            # 窗口内手动交卷：以本次提交快照为准，合并此前自动保存的答案
            valid_ids = set(session.get("question_ids") or [])
            merged = dict(session.get("answers") or {})
            for qid, value in (answers or {}).items():
                if qid in valid_ids:
                    merged[qid] = value
            await ExamService._claim_and_settle(session, merged, now)

        latest = await ExamService._wait_until_submitted(session)
        if not latest or not latest.get("is_submitted"):
            raise ValueError("考试正在结算中，请稍后查看成绩")
        return ExamService._build_result(latest)

    @staticmethod
    async def get_result(session_id: str, user_id: str) -> Optional[dict]:
        """读取成绩报告；若已到截止时间则先惰性结算，未到点且未交卷返回 None。"""
        session = await ExamService._load_session(session_id, user_id)
        if not session:
            return None

        if not session.get("is_submitted") and ExamService._is_due(session):
            await ExamService._claim_and_settle(
                session, session.get("answers") or {}, datetime.utcnow()
            )
            session = await ExamService._wait_until_submitted(session)

        if not session or not session.get("is_submitted"):
            return None
        return ExamService._build_result(session)

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

    # ------------------------------------------------------------------
    # 到点自动结算后台任务
    # ------------------------------------------------------------------

    @staticmethod
    async def ensure_indexes() -> None:
        """创建自动结算扫描所需索引（幂等）。"""
        db = get_db()
        await db.exam_sessions.create_index(
            [("is_submitted", 1), ("start_time", 1)], background=True
        )

    @staticmethod
    async def auto_settle_due_exams(limit: int = 100) -> int:
        """扫描所有未结算的考试，把已到截止时间的惰性结算掉。返回结算数量。"""
        db = get_db()
        settled_count = 0
        cursor = (
            db.exam_sessions.find({"is_submitted": False})
            .sort("start_time", 1)
            .limit(limit)
        )
        async for session in cursor:
            try:
                if await ExamService.settle_if_due(session):
                    settled_count += 1
            except Exception as exc:  # 单场考试结算失败不影响其他考试
                print(f"[exam] 自动结算 {session.get('_id')} 失败: {exc}")
        return settled_count

    @staticmethod
    async def settle_if_due(session: dict) -> bool:
        if session.get("is_submitted"):
            return False
        if not ExamService._is_due(session):
            return False
        fields = await ExamService._claim_and_settle(
            session, session.get("answers") or {}, datetime.utcnow()
        )
        return fields is not None

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    async def _load_session(session_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        if not ObjectId.is_valid(session_id):
            return None
        db = get_db()
        query: Dict[str, Any] = {"_id": ObjectId(session_id)}
        if user_id is not None:
            query["user_id"] = user_id
        return await db.exam_sessions.find_one(query)

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo else value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return None
        return None

    @staticmethod
    def _deadline(session: dict) -> Optional[datetime]:
        start = ExamService._parse_dt(session.get("start_time"))
        if not start:
            return None
        return start + timedelta(minutes=int(session.get("duration_minutes") or 0))

    @staticmethod
    def _is_due(session: dict, now: Optional[datetime] = None) -> bool:
        deadline = ExamService._deadline(session)
        if deadline is None:
            return False
        return (now or datetime.utcnow()) >= deadline

    @staticmethod
    async def _build_question_payload(session: dict) -> List[dict]:
        question_ids = session.get("question_ids", [])
        questions = await QuestionService.get_questions_by_ids(question_ids)

        result = []
        for q in questions:
            options = q.get("options")
            # 判断题种子数据可能缺少选项，补默认的“正确/错误”（答案键 A/B）
            if q["type"] == "true_false" and not options:
                options = [
                    {"key": "A", "content": "正确"},
                    {"key": "B", "content": "错误"}
                ]
            result.append({
                "id": str(q["_id"]),
                "type": q["type"],
                "content": q["content"],
                "options": options,
                "difficulty": q["difficulty"],
                "knowledge_ids": q.get("knowledge_ids", [])
            })
        return result

    @staticmethod
    async def _claim_and_settle(
        session: dict,
        answers: Dict[str, Any],
        now: datetime
    ) -> Optional[dict]:
        """
        原子认领并完成结算。并发调用只有一个能拿到结算权（Mongo 条件更新保证），
        其余调用返回 None，由调用方回读首次报告。
        """
        db = get_db()
        oid = ObjectId(session["_id"])
        stale_before = now - timedelta(seconds=SETTLE_LOCK_STALE_SECONDS)

        claim_filter = {
            "_id": oid,
            "is_submitted": False,
            "$or": [
                {"settling": {"$exists": False}},
                {"settling": None},
                {"settling": False},
                {"settle_started_at": {"$lt": stale_before}},
            ],
        }
        claim = await db.exam_sessions.find_one_and_update(
            claim_filter,
            {"$set": {"settling": True, "settle_started_at": now}}
        )
        if not claim:
            # 已有并发请求正在结算
            return None

        try:
            fields = await ExamService._grade(claim, answers, now)
        except Exception:
            # 释放锁，允许后续请求/后台任务重试
            await db.exam_sessions.update_one(
                {"_id": oid}, {"$set": {"settling": False}}
            )
            raise

        await db.exam_sessions.update_one(
            {"_id": oid},
            {
                "$set": fields,
                "$unset": {"settling": "", "settle_started_at": ""}
            }
        )

        redis = get_redis()
        if redis:
            await redis.delete(f"exam:{claim.get('user_id')}:{str(oid)}")

        return fields

    @staticmethod
    async def _grade(
        session: dict,
        answers: Dict[str, Any],
        now: datetime
    ) -> dict:
        from app.modules.practice.service import PracticeService

        question_ids = session.get("question_ids", [])
        questions = await QuestionService.get_questions_by_ids(question_ids)
        user_id = session.get("user_id")

        def normalize_answer(value: Any) -> Any:
            # 未选 / 清空的多选、None、空字符串一律按未作答处理
            if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
                return None
            return value

        correct_count = 0
        final_answers: Dict[str, Any] = {}
        details = []
        for q in questions:
            qid = str(q["_id"])
            user_answer = normalize_answer(answers.get(qid))
            final_answers[qid] = user_answer

            if user_answer is None:
                is_correct = False  # 未答题目按错误计
            else:
                is_correct = QuestionService.compare_answers(
                    q["type"], user_answer, q["correct_answer"]
                )

            if is_correct:
                correct_count += 1
            else:
                await PracticeService._add_to_errors(user_id, qid)

            options = q.get("options")
            if q["type"] == "true_false" and not options:
                options = [
                    {"key": "A", "content": "正确"},
                    {"key": "B", "content": "错误"}
                ]

            details.append({
                "question_id": qid,
                "user_answer": user_answer,
                "correct_answer": q["correct_answer"],
                "is_correct": is_correct,
                "type": q["type"],
                "content": q["content"],
                "options": options,
                "explanation": q.get("explanation")
            })

        total = len(questions)
        score = round((correct_count / total) * 100, 1) if total > 0 else 0

        start = ExamService._parse_dt(session.get("start_time")) or now
        duration_seconds = int(session.get("duration_minutes") or 0) * 60
        duration_used = max(
            0, min(int((now - start).total_seconds()), duration_seconds)
        )

        return {
            "answers": final_answers,
            "is_submitted": True,
            "score": score,
            "correct_count": correct_count,
            "total_questions": total,
            "end_time": now,
            "duration_used": duration_used,
            "details": details
        }

    @staticmethod
    async def _wait_until_submitted(session: dict, timeout_seconds: float = 10) -> Optional[dict]:
        """等待并发结算完成并回读已持久化的首次报告。"""
        db = get_db()
        oid = ObjectId(session["_id"])
        attempts = int(timeout_seconds / 0.3)
        latest = None
        for _ in range(max(attempts, 1)):
            latest = await db.exam_sessions.find_one({"_id": oid})
            if latest and latest.get("is_submitted"):
                return latest
            await asyncio.sleep(0.3)
        return latest

    @staticmethod
    def _build_result(session: dict) -> dict:
        details = session.get("details") or []
        total = session.get("total_questions") or len(details)
        correct_count = session.get("correct_count") or 0
        score = session.get("score") or 0
        return {
            "id": str(session["_id"]),
            "name": session.get("name", "模拟考试"),
            "subject_id": session.get("subject_id"),
            "score": score,
            "total_questions": total,
            "correct_count": correct_count,
            # 成绩与正确率保持同一口径
            "accuracy": score,
            "duration_used": session.get("duration_used", 0),
            "submitted_at": session.get("end_time"),
            "details": details
        }
