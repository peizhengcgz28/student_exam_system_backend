# app/core/database.py
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # 开发环境打印 SQL 语句
    pool_pre_ping=True,  # 防止连接失效
)

# ORM 模型基类
Base = declarative_base()

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 依赖注入：获取数据库会话
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# 创建数据库表
async def init_db():
    """初始化数据库，创建所有表"""
    # 重要：确保所有模型都被导入
    from app.models import user, question, paper, exam_record
    
    async with engine.begin() as conn:
        # 先删除所有旧表（开发环境）
        print("正在删除旧表...")
        await conn.run_sync(Base.metadata.drop_all)
        print("[OK] 旧表已删除")
        
        # 打印将要创建的表名（用于调试）
        print("将要创建的表:", list(Base.metadata.tables.keys()))
        await conn.run_sync(Base.metadata.create_all)
        print("[OK] 数据库表创建完成")

async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
    print("[OK] 数据库连接已关闭")