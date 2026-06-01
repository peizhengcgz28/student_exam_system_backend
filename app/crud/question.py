# app/crud/question.py
"""
题目 CRUD 操作
"""
from math import ceil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionUpdate


async def get_question_by_id(db: AsyncSession, question_id: int) -> Question | None:
    """通过 ID 查询题目"""
    result = await db.execute(
        select(Question).where(Question.id == question_id, Question.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_question_by_id_raw(db: AsyncSession, question_id: int) -> Question | None:
    """通过 ID 查询题目（不过滤 is_active）"""
    result = await db.execute(
        select(Question).where(Question.id == question_id)
    )
    return result.scalar_one_or_none()


async def get_questions_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    question_type: str | None = None,
    difficulty: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
) -> tuple[list[Question], int]:
    """
    分页查询题目列表
    
    Returns:
        tuple[list[Question], int]: (题目列表, 总条数)
    """
    # 构建基础查询条件
    conditions = [Question.is_active == True]
    
    if question_type:
        conditions.append(Question.question_type == question_type)
    if difficulty:
        conditions.append(Question.difficulty == difficulty)
    if category:
        conditions.append(Question.category == category)
    if keyword:
        # 按标题或题干内容搜索
        keyword_filter = or_(
            Question.title.ilike(f"%{keyword}%"),
            Question.content["stem"].as_string().ilike(f"%{keyword}%"),
        )
        conditions.append(keyword_filter)
    
    # 查询总数
    count_query = select(func.count(Question.id)).where(*conditions)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # 计算分页
    total_pages = ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    
    # 查询列表
    query = (
        select(Question)
        .where(*conditions)
        .offset(offset)
        .limit(page_size)
        .order_by(Question.created_at.desc())
    )
    result = await db.execute(query)
    questions = list(result.scalars().all())
    
    return questions, total


async def create_question(db: AsyncSession, question_in: QuestionCreate, user_id: int) -> Question:
    """创建新题目"""
    db_question = Question(
        title=question_in.title,
        question_type=question_in.question_type,
        difficulty=question_in.difficulty,
        content=question_in.content.model_dump(),  # 将 Pydantic 模型转为 dict
        category=question_in.category,
        score=question_in.score,
        created_by=user_id,
    )
    db.add(db_question)
    await db.commit()
    await db.refresh(db_question)
    return db_question


async def update_question(
    db: AsyncSession, db_question: Question, question_in: QuestionUpdate
) -> Question:
    """更新题目"""
    update_data = question_in.model_dump(exclude_unset=True)
    
    # 如果 content 是 QuestionContent 对象，转为 dict
    if "content" in update_data and hasattr(update_data["content"], "model_dump"):
        update_data["content"] = update_data["content"].model_dump()
    
    for field, value in update_data.items():
        setattr(db_question, field, value)
    
    await db.commit()
    await db.refresh(db_question)
    return db_question


async def delete_question(db: AsyncSession, db_question: Question) -> None:
    """
    软删除题目（将 is_active 设为 False）
    保留数据用于历史试卷引用
    """
    db_question.is_active = False
    await db.commit()


async def hard_delete_question(db: AsyncSession, db_question: Question) -> None:
    """物理删除题目（慎用）"""
    await db.delete(db_question)
    await db.commit()
