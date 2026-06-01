# app/schemas/question.py
"""
题目 Pydantic Schema - 请求/响应数据校验
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any
from app.models.question import QuestionType, DifficultyLevel


# ── 内容字段的子结构 ──────────────────────────────────
class QuestionContent(BaseModel):
    """
    题目内容 JSON 结构
    对应前端约定的格式：{"stem":"...","options":["A.xx","B.xx"],"answer":"A"}
    """
    stem: str = Field(..., description="题干")
    options: list[str] = Field(default=[], description="选项列表，如 ['A. 选项1', 'B. 选项2']")
    answer: Any = Field(default=None, description="正确答案")
    explanation: str | None = Field(default=None, description="答案解析")
    knowledge_point: str | None = Field(default=None, description="知识点")
    tags: list[str] | None = Field(default=None, description="标签")


# ── 创建题目请求 ──────────────────────────────────────
class QuestionCreate(BaseModel):
    """创建题目的请求体"""
    title: str = Field(..., min_length=1, max_length=200, description="题目标题")
    question_type: QuestionType = Field(..., description="题目类型")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM, description="难度等级")
    content: QuestionContent = Field(..., description="题目内容（题干、选项、答案等）")
    category: str | None = Field(default=None, max_length=50, description="题目分类")
    score: float = Field(default=1, ge=0, description="题目分值")


# ── 更新题目请求 ──────────────────────────────────────
class QuestionUpdate(BaseModel):
    """更新题目的请求体（所有字段可选）"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    question_type: QuestionType | None = Field(default=None)
    difficulty: DifficultyLevel | None = Field(default=None)
    content: QuestionContent | None = Field(default=None)
    category: str | None = Field(default=None, max_length=50)
    score: float | None = Field(default=None, ge=0)
    is_active: bool | None = Field(default=None)


# ── 题目列表查询参数 ──────────────────────────────────
class QuestionQueryParams(BaseModel):
    """题目列表查询参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")
    question_type: QuestionType | None = Field(default=None, description="按题型筛选")
    difficulty: DifficultyLevel | None = Field(default=None, description="按难度筛选")
    category: str | None = Field(default=None, description="按分类筛选")
    keyword: str | None = Field(default=None, description="按关键词搜索（标题/题干）")


# ── 题目响应（学生视图 - 隐藏答案） ───────────────────
class QuestionOut(BaseModel):
    """返回给客户端的题目信息（学生视图，隐藏答案）"""
    id: int
    title: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    content: dict
    category: str | None
    score: float
    is_active: bool
    created_by: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── 题目响应（教师/管理员视图 - 显示答案） ─────────────
class QuestionOutWithAnswer(QuestionOut):
    """教师视角，包含答案的题目信息"""
    pass


# ── 分页响应 ──────────────────────────────────────────
class PaginatedQuestionResponse(BaseModel):
    """分页题目列表响应（学生视图）"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[QuestionOut]


class PaginatedQuestionResponseWithAnswer(BaseModel):
    """分页题目列表响应（教师/管理员，含答案）"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[QuestionOutWithAnswer]
