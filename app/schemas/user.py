# app/schemas/user.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re


# 共享属性
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    phone: str = Field(..., min_length=11, max_length=20)
    role: str | None = Field("user", max_length=20)


# 创建用户时的请求体
class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # 简单的手机号验证（中国大陆）
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('请输入有效的手机号码')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r'[A-Za-z]', v) or not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含字母和数字')
        return v


# 更新用户（可选字段）
class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=50)
    phone: str | None = Field(None, min_length=11, max_length=20)
    role: str | None = Field(None, max_length=20)
    password: str | None = Field(None, min_length=6)


# 返回给客户端的用户信息（不含密码）
class UserOut(UserBase):
    id: int
    created_at: datetime 

    class Config:
        from_attributes = True  # SQLAlchemy 2.0 使用 from_attributes