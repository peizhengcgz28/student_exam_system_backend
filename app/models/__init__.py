# app/models/__init__.py
"""
模型导出模块

确保导入所有模型类，便于 Alembic 自动发现和数据库表创建
按照规范：显式导入并通过 __all__ 列表导出
"""

from app.models.user import User
from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.paper import Paper
from app.models.exam_record import ExamRecord

# 列出所有模型和枚举类
__all__ = [
    # 用户模型
    "User",
    
    # 题目相关
    "Question",
    "QuestionType",      # 题目类型枚举
    "DifficultyLevel",   # 难度等级枚举
    
    # 试卷相关
    "Paper",
    
    # 考试记录相关
    "ExamRecord",
]
