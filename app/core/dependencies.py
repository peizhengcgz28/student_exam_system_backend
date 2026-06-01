# app/core/dependencies.py
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token
from app.crud.user import get_user_by_id
from app.models.user import User

# 获取logger实例
logger = logging.getLogger("exam_api")

# API Key 认证方案（简单 Bearer Token）
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def get_current_user(
    authorization: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前认证用户
    
    Args:
        authorization: Authorization 请求头（格式：Bearer <token>）
        db: 数据库会话
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 如果 token 无效或用户不存在
    """
    logger.debug(f"[AUTH] Token verification started")
    
    # 从 "Bearer xxx" 中提取 token
    if not authorization:
        logger.warning("[WARN] Token verification failed - No authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except ValueError:
        logger.warning("[WARN] Token verification failed - Invalid authorization format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误，请使用: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 解码 token
    payload = decode_access_token(token)
    
    if payload is None:
        logger.warning("[WARN] Token verification failed - Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从 token 中提取用户 ID
    user_id: str | None = payload.get("sub")
    
    if user_id is None:
        logger.warning("[WARN] Token verification failed - No user ID in token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 查询用户
    user = await get_user_by_id(db, int(user_id))
    
    if user is None:
        logger.warning(f"[WARN] Token verification failed - User not found (ID: {user_id})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"[OK] Token verified - User ID: {user.id}, Name: {user.name}")
    
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
    logger.debug(f"[ACTIVE] Active user check - User ID: {current_user.id}")
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
    logger.info(f"[SUPER] Superuser check - User ID: {current_user.id}, Name: {current_user.name}")
    
    if not current_user.is_superuser:
        logger.warning(f"[DENIED] Permission denied - User {current_user.name} is not a superuser")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限",
        )
    
    logger.info(f"[OK] Superuser verified - User {current_user.name}")
    return current_user
