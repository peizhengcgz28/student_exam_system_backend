# app/api/v1/users.py
from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.user import UserOut
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息
    
    Args:
        current_user: 当前认证用户（通过 JWT token 自动验证）
        
    Returns:
        UserOut: 当前用户信息
    """
    return current_user
