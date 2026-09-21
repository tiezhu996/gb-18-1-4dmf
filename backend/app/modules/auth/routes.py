from fastapi import APIRouter, Depends, HTTPException, status
from app.modules.auth.models import UserCreate, UserLogin, UserResponse, Token
from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    try:
        user = await AuthService.create_user(user_data)
        access_token = AuthService.create_token_for_user(user)
        return Token(
            access_token=access_token,
            user=AuthService.to_response(user)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin):
    user = await AuthService.authenticate(login_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    access_token = AuthService.create_token_for_user(user)
    return Token(
        access_token=access_token,
        user=AuthService.to_response(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    return AuthService.to_response(user)
