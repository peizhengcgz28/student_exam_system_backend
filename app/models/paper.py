# app/models/paper.py
"""
试卷模型 - 存储试卷信息和题目ID列表
使用 JSON 数组存储题目 ID，支持灵活的组卷规则
"""
from sqlalchemy import String, Integer, DateTime, Boolean, func, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import JSON
from app.core.database import Base


class Paper(Base):
    """
    试卷模型
    
    question_ids JSON 数组示例：[1, 5, 8, 12, 15, ...]
    
    config JSON 字段结构示例：
    {
        "rules": {
            "single_choice_count": 10,
            "multiple_choice_count": 5,
            "true_false_count": 5,
            "fill_blank_count": 3,
            "short_answer_count": 2
        },
        "difficulty_distribution": {
            "easy": 0.3,
            "medium": 0.5,
            "hard": 0.2
        },
        "shuffle_questions": true,
        "shuffle_options": true,
        "show_score_after_submit": false
    }
    """
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # 试卷基本信息
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="试卷名称")
    description: Mapped[str] = mapped_column(String(500), nullable=True, comment="试卷描述")
    
    # 题目列表（JSON数组存储题目ID）
    question_ids: Mapped[list] = mapped_column(JSON, nullable=False, comment="题目ID列表")
    
    # 试卷配置（JSON格式，存储组卷规则、考试设置等）
    config: Mapped[dict] = mapped_column(JSON, default=dict, comment="试卷配置（组卷规则、考试设置等）")
    
    # 考试参数
    total_score: Mapped[float] = mapped_column(Float, nullable=False, comment="总分")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, comment="考试时长（分钟）")
    pass_score: Mapped[float] = mapped_column(Float, nullable=True, comment="及格分数")
    
    # 分类和标签
    category: Mapped[str] = mapped_column(String(50), nullable=True, index=True, comment="试卷分类")
    tags: Mapped[list] = mapped_column(JSON, default=list, comment="标签列表")
    
    # 状态管理
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否发布")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    
    # 统计信息
    question_count: Mapped[int] = mapped_column(Integer, default=0, comment="题目数量")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, comment="考试次数")
    
    # 审计字段
    created_by: Mapped[int] = mapped_column(Integer, nullable=True, comment="创建者ID")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    published_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True, comment="发布时间")

    def __repr__(self):
        return f"<Paper(id={self.id}, title='{self.title}', questions={len(self.question_ids)})>"
