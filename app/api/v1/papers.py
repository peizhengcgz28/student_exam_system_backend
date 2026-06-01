"""
试卷管理 API

功能：
- POST   /api/v1/papers              - 创建试卷（教师）
- GET    /api/v1/papers              - 分页获取试卷列表
- GET    /api/v1/papers/{id}         - 获取试卷详情（含题目）
- PUT    /api/v1/papers/{id}         - 更新试卷
- PATCH  /api/v1/papers/{id}/publish - 发布试卷
- DELETE /api/v1/papers/{id}         - 删除试卷

权限说明：
- 创建/更新/删除/发布需要教师或管理员角色
- 试卷发布后学生才能看到
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.paper import Paper
from app.schemas.paper import (
    PaperCreate,
    PaperUpdate,
    PaperOut,
    PaperDetailOut,
    PaperDetailOutWithAnswer,
    PaginatedPaperResponse,
)
from app.crud.paper import (
    get_paper_by_id,
    get_papers_paginated,
    get_questions_by_ids,
    create_paper,
    update_paper,
    publish_paper,
    delete_paper,
)

logger = logging.getLogger("exam_api")

router = APIRouter(prefix="/papers", tags=["试卷"])


# ── 辅助函数 ──────────────────────────────────────────

def _is_teacher(user: User) -> bool:
    """判断用户是否为教师角色"""
    return user.role == "teacher"


def _is_student(user: User) -> bool:
    """判断用户是否为教师角色"""
    return user.role == "user"


async def _get_paper_or_404(db: AsyncSession, paper_id: int) -> Paper:
    """获取试卷，不存在则 404"""
    paper = await get_paper_by_id(db, paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="试卷不存在或已删除",
        )
    return paper


def _strip_answer_from_content(content: dict) -> dict:
    """移除 content 中的答案字段"""
    student_content = content.copy()
    student_content.pop("answer", None)
    return student_content


def _build_student_question_dict(q):
    """构建学生视图的题目字典（不含答案）"""
    return {
        "id": q.id,
        "title": q.title,
        "question_type": q.question_type,
        "difficulty": q.difficulty,
        "content": _strip_answer_from_content(q.content),
        "category": q.category,
        "score": q.score,
        "is_active": q.is_active,
        "created_by": q.created_by,
        "created_at": q.created_at,
        "updated_at": q.updated_at,
    }


# ── 创建试卷 ──────────────────────────────────────────

@router.post("", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
async def create_new_paper(
    paper_in: PaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建试卷（需要教师权限）
    
    接收题目ID数组，自动计算总分
    """
    if not _is_teacher(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有教师才能创建试卷",
        )
    
    logger.info(
        f"[CREATE] Creating paper - "
        f"User: {current_user.name}, Title: {paper_in.title}, Questions: {len(paper_in.question_ids)}"
    )
    
    paper = await create_paper(db, paper_in, current_user.id)
    logger.info(f"[OK] Paper created - ID: {paper.id}, Total score: {paper.total_score}")
    
    return paper


# ── 获取试卷列表 ──────────────────────────────────────

@router.get("", response_model=PaginatedPaperResponse)
async def read_papers(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    category: str | None = Query(default=None, description="按分类筛选"),
    keyword: str | None = Query(default=None, description="关键词搜索"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分页获取试卷列表
    
    - 教师：可看到所有试卷（草稿和已发布）
    - 学生：只能看到已发布的试卷
    """
    is_teacher_user = _is_teacher(current_user)
    
    # 学生只能看到已发布的试卷
    if _is_student(current_user):
        is_published = True
    else:
        is_published = None  # 教师看到全部
    
    logger.info(
        f"[LIST] Reading papers list - "
        f"User: {current_user.name}({current_user.role}), "
        f"Page: {page}, Size: {page_size}"
    )
    
    papers, total = await get_papers_paginated(
        db,
        page=page,
        page_size=page_size,
        category=category,
        is_published=is_published,
        keyword=keyword,
    )
    
    from math import ceil
    total_pages = ceil(total / page_size) if total > 0 else 0
    
    items = [PaperOut.model_validate(p) for p in papers]
    
    return PaginatedPaperResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


# ── 获取试卷详情（含题目） ─────────────────────────────

@router.get("/{paper_id}")
async def read_paper_detail(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取试卷详情，包含题目列表
    
    - 教师：题目包含答案
    - 学生：题目隐藏答案
    """
    logger.info(
        f"[DETAIL] Reading paper detail - "
        f"User: {current_user.name}, Paper ID: {paper_id}"
    )
    
    paper = await _get_paper_or_404(db, paper_id)
    
    # 学生检查试卷是否已发布
    if _is_student(current_user) and not paper.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="试卷尚未发布，无法查看",
        )
    
    # 获取题目详情
    questions = await get_questions_by_ids(db, paper.question_ids)
    
    if _is_teacher(current_user):
        # 教师视图：包含答案
        from app.schemas.question import QuestionOutWithAnswer
        questions_out = [QuestionOutWithAnswer.model_validate(q) for q in questions]
        return PaperDetailOutWithAnswer(
            **PaperOut.model_validate(paper).model_dump(),
            questions=questions_out,
        )
    else:
        # 学生视图：隐藏答案
        from app.schemas.question import QuestionOut
        questions_out = []
        for q in questions:
            q_dict = _build_student_question_dict(q)
            questions_out.append(QuestionOut.model_validate(q_dict))
        return PaperDetailOut(
            **PaperOut.model_validate(paper).model_dump(),
            questions=questions_out,
        )


# ── 更新试卷 ──────────────────────────────────────────

@router.put("/{paper_id}", response_model=PaperOut)
async def update_existing_paper(
    paper_id: int,
    paper_in: PaperUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新试卷（需要教师权限）
    """
    if not _is_teacher(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有教师才能更新试卷",
        )
    
    logger.info(
        f"[UPDATE] Updating paper - "
        f"User: {current_user.name}, Paper ID: {paper_id}"
    )
    
    paper = await _get_paper_or_404(db, paper_id)
    
    updated_paper = await update_paper(db, paper, paper_in)
    logger.info(f"[OK] Paper updated - ID: {paper_id}")
    
    return updated_paper


# ── 发布试卷 ──────────────────────────────────────────

@router.patch("/{paper_id}/publish", response_model=PaperOut)
async def publish_existing_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    发布试卷（需要教师权限）
    
    发布后学生才能看到和参加考试
    """
    if not _is_teacher(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有教师才能发布试卷",
        )
    
    logger.info(
        f"[PUBLISH] Publishing paper - "
        f"User: {current_user.name}, Paper ID: {paper_id}"
    )
    
    paper = await _get_paper_or_404(db, paper_id)
    
    if paper.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="试卷已经发布，不能重复发布",
        )
    
    published_paper = await publish_paper(db, paper)
    logger.info(f"[OK] Paper published - ID: {paper_id}")
    
    return published_paper


# ── 删除试卷 ──────────────────────────────────────────

@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除试卷（软删除，需要教师权限）
    """
    if not _is_teacher(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有教师才能删除试卷",
        )
    
    logger.info(
        f"[DELETE] Deleting paper - "
        f"User: {current_user.name}, Paper ID: {paper_id}"
    )
    
    paper = await get_paper_by_id(db, paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="试卷不存在",
        )
    
    await delete_paper(db, paper)
    logger.info(f"[OK] Paper deleted - ID: {paper_id}")
    
    return None
