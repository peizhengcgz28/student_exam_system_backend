# app/models/question.py
"""
题目模型 - 支持多种题型（单选、多选、判断、填空等）
使用 JSON 字段灵活存储题干、选项、答案等内容
"""
from sqlalchemy import String, Integer, DateTime, Boolean, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import JSON
import enum
from app.core.database import Base


class QuestionType(enum.Enum):
    """题目类型枚举"""
    SINGLE_CHOICE = "single_choice"      # 单选题
    MULTIPLE_CHOICE = "multiple_choice"  # 多选题
    TRUE_FALSE = "true_false"            # 判断题
    FILL_BLANK = "fill_blank"            # 填空题
    SHORT_ANSWER = "short_answer"        # 简答题
    ESSAY = "essay"                      # 论述题


class DifficultyLevel(enum.Enum):
    """难度等级枚举"""
    EASY = "easy"        # 简单
    MEDIUM = "medium"    # 中等
    HARD = "hard"        # 困难


class Question(Base):
    """
    题目模型
    
    content JSON 字段结构示例：
    {
        "stem": "题干内容",
        "options": [
            {"key": "A", "value": "选项A内容"},
            {"key": "B", "value": "选项B内容"},
            ...
        ],
        "answer": "正确答案（单选：'A'，多选：['A', 'C']，判断：true/false）",
        "explanation": "答案解析",
        "knowledge_point": "知识点标签",
        "tags": ["标签1", "标签2"]
    }
    """
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # 题目基本信息
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="题目标题")
    question_type: Mapped[QuestionType] = mapped_column(SQLEnum(QuestionType), nullable=False, comment="题目类型")
    difficulty: Mapped[DifficultyLevel] = mapped_column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM, comment="难度等级")
    
    # 题目内容（JSON格式，灵活存储各种题型的数据）
    content: Mapped[dict] = mapped_column(JSON, nullable=False, comment="题目内容（题干、选项、答案等）")
    
    # 分类和标签
    category: Mapped[str] = mapped_column(String(50), nullable=True, index=True, comment="题目分类")
    tags: Mapped[list] = mapped_column(JSON, default=list, comment="标签列表")
    
    # 分值（默认1分）
    score: Mapped[float] = mapped_column(Integer, default=1, comment="题目分值")
    
    # 状态管理
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    
    # 审计字段
    created_by: Mapped[int] = mapped_column(Integer, nullable=True, comment="创建者ID")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Question(id={self.id}, type={self.question_type.value}, difficulty={self.difficulty.value})>"
