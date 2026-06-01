# app/api/v1/questions.py
"""
题库 CRUD API

功能：
- GET  /api/v1/questions        - 分页获取题目列表（学生不显示答案，教师显示答案）
- POST /api/v1/questions        - 创建新题目
- GET  /api/v1/questions/{id}   - 获取单题详情
- PUT  /api/v1/questions/{id}   - 更新题目（仅所有者）
- DELETE /api/v1/questions/{id} - 删除题目（仅所有者）

权限说明：
- 所有接口都需要登录认证
- 教师角色可查看答案
- 修改/删除需验证 created_by 为当前用户
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.question import Question
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionOut,
    QuestionOutWithAnswer,
    PaginatedQuestionResponse,
    PaginatedQuestionResponseWithAnswer,
)
from app.crud.question import (
    get_question_by_id,
    get_questions_paginated,
    create_question,
    update_question,
    delete_question,
)

# 获取logger实例
logger = logging.getLogger("exam_api")

router = APIRouter(prefix="/questions", tags=["题库"])

# ── 辅助函数 ──────────────────────────────────────────

def _strip_answer_from_content(content: dict) -> dict:
    """
    移除 content 中的答案字段，生成学生视图
    """
    student_content = content.copy()
    student_content.pop("answer", None)
    return student_content


async def _verify_question_owner(question: Question, current_user: User) -> None:
    """
    验证当前用户是否为题目的所有者
    
    Raises:
        HTTPException 403: 如果不是所有者
    """
    if question.created_by != current_user.id:
        logger.warning(
            f"[DENIED] Permission denied - User {current_user.id} "
            f"is not the owner of question {question.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：你只能操作自己创建的题目",
        )


async def _get_question_or_404(db: AsyncSession, question_id: int) -> Question:
    """
    获取题目，不存在则返回 404
    """
    question = await get_question_by_id(db, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在或已删除",
        )
    return question


# ── 辅助函数：根据角色判断是否显示答案 ────────────────
def _is_teacher(user: User) -> bool:
    """判断用户是否为教师角色"""
    return user.role == "teacher"


# ── 公共接口 ──────────────────────────────────────────

@router.get("", response_model=PaginatedQuestionResponse | PaginatedQuestionResponseWithAnswer)
async def read_questions(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    question_type: str | None = Query(default=None, description="按题型筛选"),
    difficulty: str | None = Query(default=None, description="按难度筛选"),
    category: str | None = Query(default=None, description="按分类筛选"),
    keyword: str | None = Query(default=None, description="关键词搜索"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分页获取题目列表
    
    - 教师角色：返回包含答案的完整题目信息
    - 学生角色：返回不包含答案的题目信息
    """
    logger.info(
        f"[LIST] Reading questions list - "
        f"User: {current_user.name}({current_user.role}), "
        f"Page: {page}, Size: {page_size}"
    )
    
    questions, total = await get_questions_paginated(
        db,
        page=page,
        page_size=page_size,
        question_type=question_type,
        difficulty=difficulty,
        category=category,
        keyword=keyword,
    )
    
    # 计算总页数
    from math import ceil
    total_pages = ceil(total / page_size) if total > 0 else 0
    
    # 根据角色决定是否显示答案
    is_teacher_user = _is_teacher(current_user)
    
    if is_teacher_user:
        items = [QuestionOutWithAnswer.model_validate(q) for q in questions]
        return PaginatedQuestionResponseWithAnswer(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=items,
        )
    else:
        # 学生视图：构造不包含答案的 QuestionOut
        items = []
        for q in questions:
            q_dict = {
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
            items.append(QuestionOut.model_validate(q_dict))
        
        return PaginatedQuestionResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=items,
        )


@router.get("/{question_id}", response_model=QuestionOut | QuestionOutWithAnswer)
async def read_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取单题详情
    
    - 教师角色：返回包含答案的完整题目
    - 学生角色：返回不包含答案的题目
    """
    logger.info(
        f"[DETAIL] Reading question detail - "
        f"User: {current_user.name}, Question ID: {question_id}"
    )
    
    question = await _get_question_or_404(db, question_id)
    
    if _is_teacher(current_user):
        return QuestionOutWithAnswer.model_validate(question)
    else:
        q_dict = {
            "id": question.id,
            "title": question.title,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
            "content": _strip_answer_from_content(question.content),
            "category": question.category,
            "score": question.score,
            "is_active": question.is_active,
            "created_by": question.created_by,
            "created_at": question.created_at,
            "updated_at": question.updated_at,
        }
        return QuestionOut.model_validate(q_dict)


@router.post("", response_model=QuestionOutWithAnswer, status_code=status.HTTP_201_CREATED)
async def create_new_question(
    question_in: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建新题目
    
    任何已登录用户都可以创建题目
    创建者自动设为当前用户
    """
    logger.info(
        f"[CREATE] Creating question - "
        f"User: {current_user.name}(ID: {current_user.id}), "
        f"Title: {question_in.title}"
    )
    
    question = await create_question(db, question_in, current_user.id)
    
    logger.info(f"[OK] Question created successfully - ID: {question.id}")
    
    return QuestionOutWithAnswer.model_validate(question)


@router.put("/{question_id}", response_model=QuestionOutWithAnswer)
async def update_existing_question(
    question_id: int,
    question_in: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新题目
    
    权限要求：
    - 仅题目所有者可更新
    - 非所有者返回 403
    """
    logger.info(
        f"[UPDATE] Updating question - "
        f"User: {current_user.name}(ID: {current_user.id}), "
        f"Question ID: {question_id}"
    )
    
    # 获取题目（不过滤 is_active，允许恢复已删除题目）
    from app.crud.question import get_question_by_id_raw
    question = await get_question_by_id_raw(db, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在",
        )
    
    # 验证所有者
    await _verify_question_owner(question, current_user)
    
    # 执行更新
    updated_question = await update_question(db, question, question_in)
    
    logger.info(f"[OK] Question updated successfully - ID: {question_id}")
    
    return QuestionOutWithAnswer.model_validate(updated_question)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除题目（软删除）
    
    权限要求：
    - 仅题目所有者可删除
    - 非所有者返回 403
    - 删除后 is_active 设为 False，数据保留
    """
    logger.info(
        f"[DELETE] Deleting question - "
        f"User: {current_user.name}(ID: {current_user.id}), "
        f"Question ID: {question_id}"
    )
    
    # 获取题目（不过滤 is_active，避免重复删除报错）
    from app.crud.question import get_question_by_id_raw
    question = await get_question_by_id_raw(db, question_id)
    if not question:
        logger.warning(f"[WARN] Delete failed - Question {question_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在",
        )
    
    # 验证所有者
    await _verify_question_owner(question, current_user)
    
    # 执行删除（软删除）
    await delete_question(db, question)
    
    logger.info(f"[OK] Question deleted successfully - ID: {question_id}")
    
    return None
