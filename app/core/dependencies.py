# app/core/dependencies.py
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token
from app.crud.user import get_user_by_id
from app.models.user import User

# 获取logger实例
logger = logging.getLogger("exam_api")

# OAuth2 密码流方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前认证用户
    
    Args:
        token: JWT token（从请求头中自动提取）
        db: 数据库会话
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 如果 token 无效或用户不存在
    """
    logger.debug(f"🔍 Token verification started")
    
    # 解码 token
    payload = decode_access_token(token)
    
    if payload is None:
        logger.warning("⚠️  Token verification failed - Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从 token 中提取用户 ID
    user_id: str | None = payload.get("sub")
    
    if user_id is None:
        logger.warning("⚠️  Token verification failed - No user ID in token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 查询用户
    user = await get_user_by_id(db, int(user_id))
    
    if user is None:
        logger.warning(f"⚠️  Token verification failed - User not found (ID: {user_id})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"✅ Token verified - User ID: {user.id}, Name: {user.name}")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        User: 当前用户
    """
    logger.debug(f"👤 Active user check - User ID: {current_user.id}")
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前超级管理员用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        User: 当前超级管理员用户
        
    Raises:
        HTTPException: 如果用户不是超级管理员
    """
    logger.info(f"🛡️  Superuser check - User ID: {current_user.id}, Name: {current_user.name}")
    
    if not current_user.is_superuser:
        logger.warning(f"❌ Permission denied - User {current_user.name} is not a superuser")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限",
        )
    
    logger.info(f"✅ Superuser verified - User {current_user.name}")
    return current_user
