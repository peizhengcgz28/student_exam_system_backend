"""
试卷 CRUD 操作
"""
from math import ceil
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.paper import Paper
from app.models.question import Question
from app.schemas.paper import PaperCreate, PaperUpdate


async def get_paper_by_id(db: AsyncSession, paper_id: int) -> Paper | None:
    """通过 ID 查询试卷"""
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_paper_by_id_raw(db: AsyncSession, paper_id: int) -> Paper | None:
    """通过 ID 查询试卷（不过滤 is_active）"""
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id)
    )
    return result.scalar_one_or_none()


async def get_papers_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    is_published: bool | None = None,
    keyword: str | None = None,
    only_published_for_student: bool = False,
) -> tuple[list[Paper], int]:
    """
    分页查询试卷列表
    
    Args:
        only_published_for_student: 如果为 True，学生只能看到已发布的试卷
    
    Returns:
        tuple[list[Paper], int]: (试卷列表, 总条数)
    """
    conditions = [Paper.is_active == True]
    
    if category:
        conditions.append(Paper.category == category)
    if is_published is not None:
        conditions.append(Paper.is_published == is_published)
    if keyword:
        conditions.append(Paper.title.ilike(f"%{keyword}%"))
    
    # 查询总数
    count_query = select(func.count(Paper.id)).where(*conditions)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # 分页
    total_pages = ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    
    query = (
        select(Paper)
        .where(*conditions)
        .offset(offset)
        .limit(page_size)
        .order_by(Paper.created_at.desc())
    )
    result = await db.execute(query)
    papers = list(result.scalars().all())
    
    return papers, total


async def get_questions_by_ids(
    db: AsyncSession, question_ids: list[int]
) -> list[Question]:
    """根据题目ID列表批量查询题目（仅查询启用的题目）"""
    result = await db.execute(
        select(Question).where(
            Question.id.in_(question_ids),
            Question.is_active == True
        )
    )
    return list(result.scalars().all())


async def calculate_total_score(
    db: AsyncSession, question_ids: list[int]
) -> float:
    """根据题目ID列表计算总分"""
    questions = await get_questions_by_ids(db, question_ids)
    return sum(q.score for q in questions)


async def create_paper(
    db: AsyncSession, paper_in: PaperCreate, user_id: int
) -> Paper:
    """创建试卷"""
    # 计算总分
    total_score = await calculate_total_score(db, paper_in.question_ids)
    
    db_paper = Paper(
        title=paper_in.title,
        description=paper_in.description,
        question_ids=paper_in.question_ids,
        total_score=total_score,
        duration_minutes=paper_in.duration_minutes,
        pass_score=paper_in.pass_score,
        category=paper_in.category,
        question_count=len(paper_in.question_ids),
        created_by=user_id,
    )
    db.add(db_paper)
    await db.commit()
    await db.refresh(db_paper)
    return db_paper


async def update_paper(
    db: AsyncSession, db_paper: Paper, paper_in: PaperUpdate
) -> Paper:
    """更新试卷"""
    update_data = paper_in.model_dump(exclude_unset=True)
    
    # 如果更新了题目列表，重新计算总分
    if "question_ids" in update_data:
        total_score = await calculate_total_score(db, update_data["question_ids"])
        update_data["total_score"] = total_score
        update_data["question_count"] = len(update_data["question_ids"])
    
    for field, value in update_data.items():
        setattr(db_paper, field, value)
    
    await db.commit()
    await db.refresh(db_paper)
    return db_paper


async def publish_paper(db: AsyncSession, db_paper: Paper) -> Paper:
    """发布试卷"""
    db_paper.is_published = True
    db_paper.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_paper)
    return db_paper


async def delete_paper(db: AsyncSession, db_paper: Paper) -> None:
    """软删除试卷"""
    db_paper.is_active = False
    await db.commit()
