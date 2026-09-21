from typing import Optional, List
from bson import ObjectId
from datetime import datetime
from app.core.database import get_db
from app.modules.knowledge.models import (
    KnowledgeNodeCreate, KnowledgeNodeUpdate,
    KnowledgeNodeResponse, SubjectCreate, SubjectResponse
)


class KnowledgeService:
    @staticmethod
    async def get_subjects() -> List[dict]:
        db = get_db()
        subjects = await db.subjects.find().sort("name", 1).to_list(length=None)

        result = []
        for subject in subjects:
            question_count = await db.questions.count_documents({"subject_id": str(subject["_id"])})
            chapter_count = await db.knowledge_nodes.count_documents({
                "subject_id": str(subject["_id"]),
                "level": 1
            })
            result.append({
                **subject,
                "id": str(subject["_id"]),
                "_id": str(subject["_id"]),
                "question_count": question_count,
                "chapter_count": chapter_count
            })
        return result

    @staticmethod
    async def create_subject(subject_data: SubjectCreate) -> dict:
        db = get_db()
        subject_dict = {
            **subject_data.model_dump(),
            "created_at": datetime.utcnow()
        }
        result = await db.subjects.insert_one(subject_dict)
        subject_dict["id"] = str(result.inserted_id)
        subject_dict["_id"] = str(result.inserted_id)
        return subject_dict

    @staticmethod
    async def get_knowledge_tree(subject_id: str) -> List[dict]:
        db = get_db()
        nodes = await db.knowledge_nodes.find(
            {"subject_id": subject_id}
        ).sort("order", 1).to_list(length=None)

        node_dict = {}
        for node in nodes:
            node_id = str(node["_id"])
            question_count = await db.questions.count_documents({
                "knowledge_ids": {"$in": [node_id]}
            })
            node_dict[node_id] = {
                **node,
                "id": node_id,
                "_id": node_id,
                "question_count": question_count,
                "children": []
            }

        roots = []
        for node in node_dict.values():
            parent_id = node.get("parent_id")
            if parent_id and parent_id in node_dict:
                node_dict[parent_id]["children"].append(node)
            else:
                roots.append(node)

        return roots

    @staticmethod
    async def create_knowledge_node(node_data: KnowledgeNodeCreate) -> dict:
        db = get_db()
        node_dict = {
            **node_data.model_dump(),
            "created_at": datetime.utcnow()
        }
        result = await db.knowledge_nodes.insert_one(node_dict)
        node_dict["id"] = str(result.inserted_id)
        node_dict["_id"] = str(result.inserted_id)
        node_dict["question_count"] = 0
        node_dict["children"] = []
        return node_dict

    @staticmethod
    async def search_knowledge(subject_id: str, keyword: str) -> List[dict]:
        db = get_db()
        query = {
            "subject_id": subject_id,
            "name": {"$regex": keyword, "$options": "i"}
        }
        nodes = await db.knowledge_nodes.find(query).to_list(length=50)
        result = []
        for node in nodes:
            question_count = await db.questions.count_documents({
                "knowledge_ids": {"$in": [str(node["_id"])]}
            })
            result.append({
                **node,
                "id": str(node["_id"]),
                "_id": str(node["_id"]),
                "question_count": question_count
            })
        return result

    @staticmethod
    async def get_node_by_id(node_id: str) -> Optional[dict]:
        db = get_db()
        if not ObjectId.is_valid(node_id):
            return None
        node = await db.knowledge_nodes.find_one({"_id": ObjectId(node_id)})
        if node:
            question_count = await db.questions.count_documents({
                "knowledge_ids": {"$in": [node_id]}
            })
            return {
                **node,
                "id": str(node["_id"]),
                "_id": str(node["_id"]),
                "question_count": question_count
            }
        return None
