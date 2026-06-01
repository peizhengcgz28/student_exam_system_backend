"""
考试记录 Pydantic Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime
from app.schemas.question import QuestionOut


# ── 开始考试请求 ──────────────────────────────────────
class ExamStartRequest(BaseModel):
    """开始考试请求"""
    paper_id: int = Field(..., description="试卷ID")


# ── 提交答案请求 ──────────────────────────────────────
class AnswerItem(BaseModel):
    """单题答案"""
    answer: str | list | bool | None = Field(default=None, description="用户答案")
    time_spent: int = Field(default=0, ge=0, description="该题用时（秒）")


class ExamSubmitRequest(BaseModel):
    """提交答案请求"""
    paper_id: int = Field(..., description="试卷ID")
    answers: dict[str, AnswerItem] = Field(..., description="答题记录，key为题目ID字符串")


# ── 考试记录响应 ──────────────────────────────────────
class ExamRecordOut(BaseModel):
    """考试记录响应"""
    id: int
    user_id: int
    paper_id: int
    status: str
    score: float | None
    max_score: float
    correct_count: int
    wrong_count: int
    unanswered_count: int
    started_at: datetime
    submitted_at: datetime | None
    graded_at: datetime | None
    total_time_seconds: int | None

    class Config:
        from_attributes = True


class ExamRecordDetailOut(ExamRecordOut):
    """考试详情（含题目和答案结果）"""
    answers: dict
    result: dict | None
    questions: list[QuestionOut] = []


# ── 开始考试响应（含试卷题目） ─────────────────────────
class ExamStartOut(BaseModel):
    """开始考试响应"""
    record: ExamRecordOut
    paper_title: str
    paper_description: str | None
    duration_minutes: int
    pass_score: float | None
    questions: list[QuestionOut]


# ── 提交考试响应 ──────────────────────────────────────
class ExamSubmitOut(BaseModel):
    """提交考试响应"""
    record: ExamRecordOut
    result: dict


# ── 成绩列表响应 ──────────────────────────────────────
class ExamRecordListItem(BaseModel):
    """成绩列表中的单项"""
    id: int
    user_id: int
    user_name: str | None = None
    paper_id: int
    paper_title: str | None = None
    status: str
    score: float | None
    max_score: float
    correct_count: int
    wrong_count: int
    unanswered_count: int
    accuracy: float | None = None
    total_time_seconds: int | None
    started_at: datetime
    submitted_at: datetime | None

    class Config:
        from_attributes = True


class PaginatedExamRecordResponse(BaseModel):
    """分页成绩列表响应"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[ExamRecordListItem]

