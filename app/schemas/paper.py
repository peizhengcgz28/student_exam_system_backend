"""
试卷 Pydantic Schema - 请求/响应数据校验
"""
from pydantic import BaseModel, Field
from datetime import datetime
from app.schemas.question import QuestionOut, QuestionOutWithAnswer


# ── 创建试卷请求 ──────────────────────────────────────
class PaperCreate(BaseModel):
    """创建试卷的请求体"""
    title: str = Field(..., min_length=1, max_length=200, description="试卷名称")
    description: str | None = Field(default=None, max_length=500, description="试卷描述")
    question_ids: list[int] = Field(..., min_length=1, description="题目ID数组")
    duration_minutes: int = Field(default=60, ge=1, description="考试时长（分钟）")
    pass_score: float | None = Field(default=None, ge=0, description="及格分数")
    category: str | None = Field(default=None, max_length=50, description="试卷分类")


# ── 更新试卷请求 ──────────────────────────────────────
class PaperUpdate(BaseModel):
    """更新试卷的请求体（所有字段可选）"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    question_ids: list[int] | None = Field(default=None, min_length=1)
    duration_minutes: int | None = Field(default=None, ge=1)
    pass_score: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=50)


# ── 试卷基础响应 ──────────────────────────────────────
class PaperOut(BaseModel):
    """试卷基本信息（不含题目详情）"""
    id: int
    title: str
    description: str | None
    question_ids: list
    total_score: float
    duration_minutes: int
    pass_score: float | None
    category: str | None
    is_published: bool
    question_count: int
    attempt_count: int
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None

    class Config:
        from_attributes = True


# ── 试卷详情（学生视图 - 题目不含答案） ────────────────
class PaperDetailOut(PaperOut):
    """试卷详情，包含题目列表（学生视图，隐藏答案）"""
    questions: list[QuestionOut] = []


# ── 试卷详情（教师视图 - 题目含答案） ──────────────────
class PaperDetailOutWithAnswer(PaperOut):
    """试卷详情，包含题目列表（教师视图，含答案）"""
    questions: list[QuestionOutWithAnswer] = []


# ── 分页响应 ──────────────────────────────────────────
class PaginatedPaperResponse(BaseModel):
    """分页试卷列表响应"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[PaperOut]
