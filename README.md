# 学生作答系统 - 后端服务

- 基于 FastAPI 的后端 API 服务，为前端提供数据接口，并与 AI 微服务交互。

## 技术栈 (参考)

- Python 3.10+
- FastAPI
- SQLAlchemy (ORM)
- MySQL 8.0+
- Alembic (数据库迁移)
- Redis
- JWT 鉴权
- pytest (测试)

## 项目结构 (参考)

```
backend/
├── app/
│ ├── api/ # 路由与接口
│ │ ├── v1/
│ │ │ ├── auth.py # 认证相关接口
│ │ │ ├── questions.py
│ │ │ ├── papers.py
│ │ │ ├── exams.py
│ │ │ └── ai.py # AI 服务代理接口
│ ├── core/ # 配置、安全、数据库连接
│ │ ├── config.py
│ │ ├── security.py
│ │ └── database.py
│ ├── models/ # SQLAlchemy 数据模型
│ ├── schemas/ # Pydantic 请求/响应模型
│ ├── services/ # 业务逻辑层
│ └── main.py # 应用入口
├── alembic/ # 数据库迁移脚本
├── tests/ # 单元测试
├── requirements.txt
├── .env.example
└── README.md
```


## 环境准备

1. **安装依赖**
   
```bash
pip install -r requirements.txt
```

2. 环境变量

> .env 并修改配置：

```ini
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/student_exam_system
SECRET_KEY=your-secret-key
AI_SERVICE_BASE_URL=http://localhost:8001/api/v1
REDIS_URL=redis://localhost:6379/0
```

3. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

## API 文档

- 启动后访问 http://localhost:8000/docs 查看 Swagger 交互文档。