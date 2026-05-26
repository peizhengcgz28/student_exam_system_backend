# app/api/v1/auth.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.crud.user import get_user_by_name, get_user_by_phone, create_user
from app.schemas.user import UserCreate, UserOut
from app.schemas.token import Token

# 获取logger实例
logger = logging.getLogger("exam_api")

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    用户注册
    
    Args:
        user_in: 用户注册信息
        db: 数据库会话
        
    Returns:
        UserOut: 创建的用户信息
        
    Raises:
        HTTPException: 如果用户名或手机号已存在
    """
    logger.info(f"📝 Registration attempt for user: {user_in.name}, phone: {user_in.phone}")
    
    # 检查用户名是否已存在
    existing_user = await get_user_by_name(db, name=user_in.name)
    if existing_user:
        logger.warning(f"⚠️  Registration failed - Username already exists: {user_in.name}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被使用",
        )
    
    # 检查手机号是否已存在
    existing_user = await get_user_by_phone(db, phone=user_in.phone)
    if existing_user:
        logger.warning(f"⚠️  Registration failed - Phone already exists: {user_in.phone}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已被注册",
        )
    
    # 创建新用户
    user = await create_user(db, user_in=user_in)
    logger.info(f"✅ User registered successfully: ID={user.id}, Name={user.name}")
    
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    
    Args:
        form_data: 登录表单数据（username 和 password）
        db: 数据库会话
        
    Returns:
        Token: JWT 访问令牌
        
    Raises:
        HTTPException: 如果用户名或密码错误
    """
    logger.info(f"🔑 Login attempt for user: {form_data.username}")
    
    # 通过用户名查询用户（OAuth2PasswordRequestForm 的 username 字段）
    user = await get_user_by_name(db, name=form_data.username)
    
    # 验证用户是否存在且密码正确
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"❌ Login failed - Invalid credentials for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},  # 将用户 ID 放入 token
        expires_delta=access_token_expires
    )
    
    logger.info(f"✅ Login successful - User ID: {user.id}, Token issued")
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
