"""
考试记录 CRUD 操作
"""
from math import ceil
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.exam_record import ExamRecord
from app.models.paper import Paper
from app.models.question import Question, QuestionType


async def get_in_progress_record(
    db: AsyncSession, user_id: int, paper_id: int
) -> ExamRecord | None:
    """查询用户对某试卷的进行中的记录"""
    result = await db.execute(
        select(ExamRecord).where(
            ExamRecord.user_id == user_id,
            ExamRecord.paper_id == paper_id,
            ExamRecord.status == "in_progress",
        )
    )
    return result.scalar_one_or_none()


async def create_exam_record(
    db: AsyncSession, user_id: int, paper: Paper
) -> ExamRecord:
    """创建考试记录（开始考试）"""
    record = ExamRecord(
        user_id=user_id,
        paper_id=paper.id,
        status="in_progress",
        answers={},
        max_score=paper.total_score,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_records_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    paper_id: int | None = None,
    student_id: int | None = None,
    user_id: int | None = None,
    is_teacher: bool = False,
) -> tuple[list[ExamRecord], int]:
    """
    分页查询考试记录（成绩）

    权限逻辑：
    - 教师：可查所有记录，可按 paper_id 和 student_id 筛选
    - 学生：只能查自己的记录，只能按 paper_id 筛选
    """
    conditions = []

    if paper_id:
        conditions.append(ExamRecord.paper_id == paper_id)

    if student_id and is_teacher:
        conditions.append(ExamRecord.user_id == student_id)

    if not is_teacher:
        conditions.append(ExamRecord.user_id == user_id)

    count_query = select(func.count(ExamRecord.id)).where(*conditions)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    total_pages = ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    query = (
        select(ExamRecord)
        .where(*conditions)
        .offset(offset)
        .limit(page_size)
        .order_by(desc(ExamRecord.started_at))
    )
    result = await db.execute(query)
    records = list(result.scalars().all())

    return records, total


async def get_record_by_id(
    db: AsyncSession, record_id: int
) -> ExamRecord | None:
    """通过 ID 查询考试记录"""
    result = await db.execute(
        select(ExamRecord).where(ExamRecord.id == record_id)
    )
    return result.scalar_one_or_none()


async def submit_and_grade_exam(
    db: AsyncSession,
    record: ExamRecord,
    answers: dict,
    questions: list[Question],
) -> ExamRecord:
    """提交答卷并自动批改"""
    correct_count = 0
    wrong_count = 0
    unanswered_count = 0
    total_score = 0.0
    question_details = []

    for q in questions:
        q_id_str = str(q.id)
        user_answer_item = answers.get(q_id_str)

        if user_answer_item is None:
            unanswered_count += 1
            question_details.append({
                "question_id": q.id,
                "user_answer": None,
                "correct_answer": q.content.get("answer"),
                "is_correct": False,
                "score": 0,
                "max_score": q.score,
                "time_spent": 0,
            })
            continue

        user_answer = user_answer_item.get("answer")
        time_spent = user_answer_item.get("time_spent", 0)
        correct_answer = q.content.get("answer")

        is_correct = await _auto_grade(q, user_answer, correct_answer)

        if is_correct:
            correct_count += 1
            earned_score = q.score
        else:
            wrong_count += 1
            earned_score = 0

        total_score += earned_score

        question_details.append({
            "question_id": q.id,
            "title": q.title,
            "question_type": q.question_type.value if hasattr(q.question_type, 'value') else q.question_type,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "score": earned_score,
            "max_score": q.score,
            "time_spent": time_spent,
        })

    now = datetime.now(timezone.utc)

    time_diff = now - record.started_at.replace(tzinfo=timezone.utc) if record.started_at else None
    total_time_seconds = int(time_diff.total_seconds()) if time_diff else 0

    record.status = "submitted"
    record.answers = {str(k) if not isinstance(k, str) else k: v for k, v in answers.items()}
    record.result = {
        "score": total_score,
        "max_score": record.max_score,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "unanswered_count": unanswered_count,
        "accuracy": round(total_score / record.max_score * 100, 2) if record.max_score > 0 else 0,
        "question_details": question_details,
    }
    record.score = total_score
    record.correct_count = correct_count
    record.wrong_count = wrong_count
    record.unanswered_count = unanswered_count
    record.submitted_at = now
    record.total_time_seconds = total_time_seconds

    await db.commit()
    await db.refresh(record)
    return record


async def _auto_grade(
    question: Question, user_answer: str | list | bool | None, correct_answer
) -> bool:
    """自动批改客观题"""
    if user_answer is None:
        return False

    q_type = question.question_type
    if hasattr(q_type, 'value'):
        q_type = q_type.value

    if q_type == QuestionType.SINGLE_CHOICE.value or q_type == "single_choice":
        return str(user_answer).strip().upper() == str(correct_answer).strip().upper()

    if q_type == QuestionType.MULTIPLE_CHOICE.value or q_type == "multiple_choice":
        if not isinstance(user_answer, list) or not isinstance(correct_answer, list):
            return False
        return set(str(x).strip().upper() for x in user_answer) == set(
            str(x).strip().upper() for x in correct_answer
        )

    if q_type == QuestionType.TRUE_FALSE.value or q_type == "true_false":
        return str(user_answer).strip().lower() == str(correct_answer).strip().lower()

    return False
