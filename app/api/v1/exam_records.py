"""
作答与评分 API

功能：
- POST /api/v1/exam-records/start  - 开始考试，创建考试记录
- POST /api/v1/exam-records/submit - 提交答案，自动批改

约束：
- 同学生同试卷只能有一条进行中的记录
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.paper import Paper
from app.models.question import Question
from app.models.exam_record import ExamRecord
from app.schemas.exam_record import (
    ExamStartRequest,
    ExamSubmitRequest,
    ExamStartOut,
    ExamSubmitOut,
    ExamRecordOut,
    ExamRecordListItem,
    PaginatedExamRecordResponse,
)
from app.schemas.question import QuestionOut
from app.crud.exam_record import (
    get_in_progress_record,
    create_exam_record,
    submit_and_grade_exam,
    get_records_paginated,
    get_record_by_id,
)
from app.crud.paper import get_paper_by_id, get_questions_by_ids
from app.crud.user import get_user_by_id

logger = logging.getLogger("exam_api")

router = APIRouter(prefix="/exam-records", tags=["考试作答"])


def _strip_answer_from_content(content: dict) -> dict:
    """移除 content 中的答案字段"""
    student_content = content.copy()
    student_content.pop("answer", None)
    return student_content


def _build_student_question_dict(q):
    """构建学生视图的题目字典"""
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


async def _get_published_paper_or_404(db: AsyncSession, paper_id: int) -> Paper:
    """获取已发布的试卷，不存在则404"""
    paper = await get_paper_by_id(db, paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="试卷不存在或已删除",
        )
    if not paper.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="试卷尚未发布，无法开始考试",
        )
    return paper


# ── 开始考试 ──────────────────────────────────────────

@router.post("/start", response_model=ExamStartOut)
async def start_exam(
    req: ExamStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    开始考试
    
    1. 检查试卷是否存在且已发布
    2. 检查是否有进行中的记录（防止重复考试）
    3. 创建考试记录
    4. 返回试卷内容（不含答案）
    """
    logger.info(
        f"[START] Starting exam - User: {current_user.name}(ID: {current_user.id}), "
        f"Paper ID: {req.paper_id}"
    )
    
    # 获取试卷
    paper = await _get_published_paper_or_404(db, req.paper_id)
    
    # 检查是否已有进行中的记录
    existing = await get_in_progress_record(db, current_user.id, req.paper_id)
    if existing:
        logger.warning(
            f"[WARN] Exam already in progress - User: {current_user.id}, "
            f"Paper: {req.paper_id}, Record ID: {existing.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="你已经有该试卷的进行中考试，请先提交或继续作答",
        )
    
    # 创建考试记录
    record = await create_exam_record(db, current_user.id, paper)
    
    # 获取题目（不含答案）
    questions = await get_questions_by_ids(db, paper.question_ids)
    questions_out = []
    for q in questions:
        q_dict = _build_student_question_dict(q)
        questions_out.append(QuestionOut.model_validate(q_dict))
    
    logger.info(f"[OK] Exam started - Record ID: {record.id}, Questions: {len(questions_out)}")
    
    return ExamStartOut(
        record=ExamRecordOut.model_validate(record),
        paper_title=paper.title,
        paper_description=paper.description,
        duration_minutes=paper.duration_minutes,
        pass_score=paper.pass_score,
        questions=questions_out,
    )


# ── 提交考试 ──────────────────────────────────────────

@router.post("/submit", response_model=ExamSubmitOut)
async def submit_exam(
    req: ExamSubmitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    提交答案，自动批改
    
    1. 查找用户的进行中的考试记录
    2. 获取试卷所有题目
    3. 逐题批改客观题（单选、多选、判断）
    4. 计算得分
    5. 更新考试记录
    """
    logger.info(
        f"[SUBMIT] Submitting exam - User: {current_user.name}(ID: {current_user.id})"
    )

    # 查找用户对该试卷进行中的记录
    result = await db.execute(
        select(ExamRecord).where(
            ExamRecord.user_id == current_user.id,
            ExamRecord.paper_id == req.paper_id,
            ExamRecord.status == "in_progress",
        ).order_by(desc(ExamRecord.started_at)).limit(1)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有找到进行中的考试，请先开始考试",
        )
    
    # 获取试卷题目
    paper = await get_paper_by_id(db, record.paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="试卷不存在",
        )
    
    questions = await get_questions_by_ids(db, paper.question_ids)

    # 转换 answers 格式
    answers_dict = {}
    for q_id_str, answer_item in req.answers.items():
        answers_dict[q_id_str] = {
            "answer": answer_item.answer,
            "time_spent": answer_item.time_spent,
        }
    
    # 提交并批改
    record = await submit_and_grade_exam(db, record, answers_dict, questions)
    
    logger.info(
        f"[OK] Exam submitted - Record ID: {record.id}, "
        f"Score: {record.score}/{record.max_score}, "
        f"Correct: {record.correct_count}, Wrong: {record.wrong_count}"
    )
    
    return ExamSubmitOut(
        record=ExamRecordOut.model_validate(record),
        result=record.result,
    )


# ── 辅助函数 ──────────────────────────────────────────

def _is_teacher(user: User) -> bool:
    """判断用户是否为教师角色"""
    return user.role == "teacher"


# ── 成绩查询 ──────────────────────────────────────────

@router.get("", response_model=PaginatedExamRecordResponse)
async def read_exam_records(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    paper_id: int | None = Query(default=None, description="按试卷ID筛选"),
    student_id: int | None = Query(default=None, description="按学生ID筛选（仅教师可用）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询考试成绩（按角色返回数据）

    - 教师：可查看所有成绩，可按 paper_id / student_id 筛选
    - 学生：只能查看自己的成绩，仅可按 paper_id 筛选
    """
    is_teacher_user = _is_teacher(current_user)

    logger.info(
        f"[GRADE] Querying exam records - "
        f"User: {current_user.name}({current_user.role}), "
        f"Paper: {paper_id}, Student: {student_id}"
    )

    records, total = await get_records_paginated(
        db,
        page=page,
        page_size=page_size,
        paper_id=paper_id,
        student_id=student_id,
        user_id=current_user.id,
        is_teacher=is_teacher_user,
    )

    from math import ceil
    total_pages = ceil(total / page_size) if total > 0 else 0

    items = []
    for record in records:
        paper_title = None
        paper = await get_paper_by_id(db, record.paper_id)
        if paper:
            paper_title = paper.title

        user_name = None
        if is_teacher_user:
            user = await get_user_by_id(db, record.user_id)
            if user:
                user_name = user.name

        accuracy = round(record.score / record.max_score * 100, 2) if record.max_score > 0 else None

        items.append(ExamRecordListItem(
            id=record.id,
            user_id=record.user_id,
            user_name=user_name,
            paper_id=record.paper_id,
            paper_title=paper_title,
            status=record.status,
            score=record.score,
            max_score=record.max_score,
            correct_count=record.correct_count,
            wrong_count=record.wrong_count,
            unanswered_count=record.unanswered_count,
            accuracy=accuracy,
            total_time_seconds=record.total_time_seconds,
            started_at=record.started_at,
            submitted_at=record.submitted_at,
        ))

    logger.info(f"[OK] Exam records queried - Total: {total}, Returned: {len(items)}")

    return PaginatedExamRecordResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )
