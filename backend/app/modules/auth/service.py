from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.modules.auth.models import UserCreate, UserLogin, UserResponse


class AuthService:
    @staticmethod
    async def get_by_id(user_id: str) -> Optional[dict]:
        db = get_db()
        if not ObjectId.is_valid(user_id):
            return None
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        return user

    @staticmethod
    async def get_by_username(username: str) -> Optional[dict]:
        db = get_db()
        return await db.users.find_one({"username": username})

    @staticmethod
    async def create_user(user_data: UserCreate) -> dict:
        db = get_db()
        existing_user = await db.users.find_one({"username": user_data.username})
        if existing_user:
            raise ValueError("用户名已存在")

        hashed_password = get_password_hash(user_data.password)
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hashed_password,
            "role": user_data.role,
            "created_at": datetime.utcnow(),
            "avatar": None,
            "stats": {
                "total_practiced": 0,
                "total_correct": 0,
                "streak_days": 0
            }
        }

        result = await db.users.insert_one(user_dict)
        user_dict["id"] = str(result.inserted_id)
        user_dict["_id"] = str(result.inserted_id)
        return user_dict

    @staticmethod
    async def authenticate(login_data: UserLogin) -> Optional[dict]:
        db = get_db()
        user = await db.users.find_one({"username": login_data.username})
        if not user:
            return None
        if not verify_password(login_data.password, user["hashed_password"]):
            return None
        return user

    @staticmethod
    def create_token_for_user(user: dict) -> str:
        return create_access_token(subject=str(user["_id"]))

    @staticmethod
    def to_response(user: dict) -> UserResponse:
        return UserResponse(
            id=str(user["_id"]),
            username=user.get("username", ""),
            email=user.get("email"),
            role=user.get("role", "student"),
            created_at=user.get("created_at", datetime.utcnow()),
            avatar=user.get("avatar")
        )
