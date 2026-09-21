from typing import List, Dict, Any
from bson import ObjectId
from datetime import datetime, timedelta
from app.core.database import get_db


class AnalysisService:
    @staticmethod
    async def get_learning_overview(user_id: str) -> Dict[str, Any]:
        db = get_db()

        practice_sessions = await db.practice_sessions.count_documents({
            "user_id": user_id,
            "answers": {"$exists": True, "$ne": {}}
        })

        answers_cursor = db.practice_sessions.find({"user_id": user_id}, {"answers": 1})
        all_answers = []
        async for session in answers_cursor:
            for qid, ans in session.get("answers", {}).items():
                all_answers.append(ans)

        total_practiced = len(all_answers)
        total_correct = sum(1 for a in all_answers if a.get("is_correct"))
        accuracy = round(total_correct / total_practiced * 100, 1) if total_practiced > 0 else 0

        exams = await db.exam_sessions.count_documents({
            "user_id": user_id,
            "is_submitted": True
        })

        exam_scores = []
        exam_cursor = db.exam_sessions.find(
            {"user_id": user_id, "is_submitted": True},
            {"score": 1}
        )
        async for exam in exam_cursor:
            if exam.get("score") is not None:
                exam_scores.append(exam["score"])
        avg_exam_score = round(sum(exam_scores) / len(exam_scores), 1) if exam_scores else 0

        weak_knowledge = await AnalysisService._get_weak_knowledge(user_id)

        return {
            "total_practiced": total_practiced,
            "total_correct": total_correct,
            "accuracy": accuracy,
            "total_exams": exams,
            "avg_exam_score": avg_exam_score,
            "weak_knowledge": weak_knowledge
        }

    @staticmethod
    async def _get_weak_knowledge(user_id: str, top_n: int = 5) -> List[Dict[str, Any]]:
        db = get_db()

        error_pipeline = [
            {"$match": {"user_id": user_id, "mastered": False}},
            {"$unwind": "$knowledge_ids"},
            {"$group": {
                "_id": "$knowledge_ids",
                "error_count": {"$sum": 1}
            }},
            {"$sort": {"error_count": -1}},
            {"$limit": top_n}
        ]

        error_stats = await db.errors.aggregate(error_pipeline).to_list(length=top_n)

        result = []
        for stat in error_stats:
            k_id = stat["_id"]
            if ObjectId.is_valid(k_id):
                knowledge = await db.knowledge_nodes.find_one({"_id": ObjectId(k_id)})
                if knowledge:
                    result.append({
                        "knowledge_id": k_id,
                        "knowledge_name": knowledge.get("name", "未知知识点"),
                        "error_count": stat["error_count"]
                    })
            else:
                result.append({
                    "knowledge_id": k_id,
                    "knowledge_name": k_id,
                    "error_count": stat["error_count"]
                })

        return result

    @staticmethod
    async def get_accuracy_trend(user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        db = get_db()

        start_date = datetime.utcnow() - timedelta(days=days)

        pipeline = [
            {"$match": {
                "user_id": user_id,
                "updated_at": {"$gte": start_date}
            }},
            {"$project": {
                "date": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$updated_at"
                    }
                },
                "answers": 1
            }},
            {"$unwind": {"path": "$answers", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": "$date",
                "answers": {"$push": "$answers"}
            }},
            {"$sort": {"_id": 1}}
        ]

        daily_stats = await db.practice_sessions.aggregate(pipeline).to_list(length=days)

        result = []
        for stat in daily_stats:
            answers = stat.get("answers", [])
            if isinstance(answers, list):
                correct_count = 0
                total = 0
                for ans in answers:
                    if isinstance(ans, dict):
                        total += 1
                        if ans.get("is_correct"):
                            correct_count += 1
                accuracy = round(correct_count / total * 100, 1) if total > 0 else 0
                result.append({
                    "date": stat["_id"],
                    "accuracy": accuracy,
                    "total": total,
                    "correct": correct_count
                })

        return result

    @staticmethod
    async def get_knowledge_mastery(user_id: str, subject_id: str) -> List[Dict[str, Any]]:
        db = get_db()

        knowledge_nodes = await db.knowledge_nodes.find(
            {"subject_id": subject_id, "level": 3}
        ).to_list(length=None)

        result = []
        for node in knowledge_nodes:
            node_id = str(node["_id"])
            node_name = node.get("name", "")

            practice_cursor = db.practice_sessions.find({
                "user_id": user_id
            }, {"answers": 1})

            total_answered = 0
            correct_count = 0

            async for session in practice_cursor:
                for qid, ans in session.get("answers", {}).items():
                    question = await db.questions.find_one({
                        "_id": ObjectId(qid),
                        "knowledge_ids": {"$in": [node_id]}
                    })
                    if question:
                        total_answered += 1
                        if ans.get("is_correct"):
                            correct_count += 1

            if total_answered > 0:
                result.append({
                    "knowledge_id": node_id,
                    "knowledge_name": node_name,
                    "total_answered": total_answered,
                    "correct_count": correct_count,
                    "mastery_rate": round(correct_count / total_answered * 100, 1)
                })

        return sorted(result, key=lambda x: x["mastery_rate"])

    @staticmethod
    async def get_recommendations(user_id: str) -> Dict[str, Any]:
        db = get_db()

        weak_knowledge = await AnalysisService._get_weak_knowledge(user_id, top_n=10)

        recommended_questions = []
        for wk in weak_knowledge:
            k_id = wk["knowledge_id"]
            questions = await db.questions.find({
                "knowledge_ids": {"$in": [k_id]}
            }).limit(3).to_list(length=3)

            for q in questions:
                recommended_questions.append({
                    "id": str(q["_id"]),
                    "type": q["type"],
                    "content": q["content"],
                    "difficulty": q["difficulty"],
                    "knowledge_id": k_id,
                    "knowledge_name": wk["knowledge_name"]
                })

        return {
            "weak_knowledge": weak_knowledge[:5],
            "recommended_questions": recommended_questions[:10]
        }
