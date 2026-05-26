# app/models/exam_record.py
"""
考试记录模型 - 存储用户答题情况、得分、用时等信息
"""
from sqlalchemy import String, Integer, DateTime, Boolean, func, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import JSON
from app.core.database import Base


class ExamRecord(Base):
    """
    考试记录模型
    
    answers JSON 字段结构示例：
    {
        "1": {"answer": "A", "time_spent": 30},           # 题目ID: {答案, 用时(秒)}
        "5": {"answer": ["A", "C"], "time_spent": 45},    # 多选题
        "8": {"answer": true, "time_spent": 20},          # 判断题
        "12": {"answer": "填空题答案", "time_spent": 60}   # 填空题
    }
    
    result JSON 字段结构示例：
    {
        "score": 85.5,
        "correct_count": 17,
        "wrong_count": 3,
        "unanswered_count": 0,
        "question_details": [
            {
                "question_id": 1,
                "user_answer": "A",
                "correct_answer": "A",
                "is_correct": true,
                "score": 2.0,
                "time_spent": 30
            },
            ...
        ]
    }
    """
    __tablename__ = "exam_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # 关联信息
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id"), nullable=False, index=True, comment="试卷ID")
    
    # 考试状态
    status: Mapped[str] = mapped_column(String(20), default="in_progress", comment="考试状态（in_progress/submitted/graded）")
    
    # 答题信息（JSON格式存储每道题的答案和用时）
    answers: Mapped[dict] = mapped_column(JSON, default=dict, comment="答题记录（题目ID -> 答案详情）")
    
    # 考试结果（JSON格式存储得分、正确率等详细信息）
    result: Mapped[dict] = mapped_column(JSON, nullable=True, comment="考试结果（得分、正确率、详细分析）")
    
    # 时间记录
    started_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), comment="开始时间")
    submitted_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True, comment="提交时间")
    graded_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True, comment="批改时间")
    
    # 用时统计
    total_time_seconds: Mapped[int] = mapped_column(Integer, nullable=True, comment="总用时（秒）")
    
    # 得分信息
    score: Mapped[float] = mapped_column(Float, nullable=True, comment="得分")
    max_score: Mapped[float] = mapped_column(Float, nullable=False, comment="总分")
    
    # 答题统计
    correct_count: Mapped[int] = mapped_column(Integer, default=0, comment="答对题数")
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, comment="答错题数")
    unanswered_count: Mapped[int] = mapped_column(Integer, default=0, comment="未答题数")
    
    # 其他信息
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True, comment="IP地址")
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True, comment="浏览器信息")
    remarks: Mapped[str] = mapped_column(Text, nullable=True, comment="备注")
    
    # 关系映射（可选，用于 ORM 查询）
    # user = relationship("User", back_populates="exam_records")
    # paper = relationship("Paper", back_populates="exam_records")

    def __repr__(self):
        return f"<ExamRecord(id={self.id}, user_id={self.user_id}, paper_id={self.paper_id}, status={self.status})>"
