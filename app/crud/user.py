# app/crud/user.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


async def get_user_by_name(db: AsyncSession, name: str) -> User | None:
    """通过用户名查询用户"""
    result = await db.execute(select(User).where(User.name == name))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    """通过手机号查询用户"""
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """通过 ID 查询用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """创建新用户"""
    # 对密码进行哈希处理
    hashed_password = get_password_hash(user_in.password)
    
    # 创建用户对象
    db_user = User(
        name=user_in.name,
        phone=user_in.phone,
        hashed_password=hashed_password,
        role=user_in.role if user_in.role else "user"
    )
    
    # 添加到数据库
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user


async def update_user(db: AsyncSession, db_user: User, user_in: UserUpdate) -> User:
    """更新用户信息"""
    update_data = user_in.model_dump(exclude_unset=True)
    
    # 如果提供了新密码，则进行哈希处理
    if "password" in update_data and update_data["password"] is not None:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # 更新字段
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    await db.commit()
    await db.refresh(db_user)
    
    return db_user
