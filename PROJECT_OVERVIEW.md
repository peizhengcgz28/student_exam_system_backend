# 项目文档

## 目录结构

```
app/
├── main.py                  # FastAPI 应用入口，注册中间件和路由
├── core/
│   ├── config.py            # pydantic-settings 读取 .env
│   ├── database.py          # SQLAlchemy 2.0 异步引擎 + 会话工厂
│   ├── security.py          # bcrypt 密码哈希 + JWT 生成/解码
│   └── dependencies.py      # get_current_user / get_current_superuser 依赖注入
├── models/
│   ├── user.py              # User 表
│   ├── question.py          # Question 表（模型已定义，API 未实现）
│   ├── paper.py             # Paper 表（模型已定义，API 未实现）
│   └── exam_record.py       # ExamRecord 表（模型已定义，API 未实现）
├── schemas/
│   ├── user.py              # UserCreate / UserUpdate / UserOut (Pydantic V2)
│   └── token.py             # Token / TokenPayload
├── crud/
│   ├── base.py              # 空
│   └── user.py              # 用户查重、创建、更新
└── api/
    ├── deps.py              # 空
    └── v1/
        ├── auth.py          # POST /register, POST /login
        └── users.py         # GET /me
```

## 技术栈

| 组件 | 选型 |
|------|------|
| 框架 | FastAPI 0.104+ |
| 数据库驱动 | SQLAlchemy 2.0 + aiomysql (异步) |
| 密码哈希 | passlib + bcrypt 4.0 (`CryptContext(schemes=["bcrypt"])`) |
| JWT | python-jose, HS256, 30min 过期 |
| 数据校验 | Pydantic V2 (`model_validate`, `from_attributes`) |
| 配置 | pydantic-settings, 自动读取 `.env` |

## 已实现的接口

### POST /api/v1/auth/register

[app/api/v1/auth.py:20](app/api/v1/auth.py#L20)

请求体 (JSON):
```json
{ "name": "张三", "phone": "13800138000", "password": "test123456", "role": "user" }
```

流程:
1. Pydantic 校验 — 手机号 `^1[3-9]\d{9}$`，密码必须含字母和数字
2. `get_user_by_name` / `get_user_by_phone` 查重，重复返回 400
3. `get_password_hash` → bcrypt 哈希
4. 写入 users 表，返回 UserOut (不含 hashed_password)

### POST /api/v1/auth/login

[app/api/v1/auth.py:62](app/api/v1/auth.py#L62)

OAuth2PasswordRequestForm (表单: `username=xxx&password=xxx`)

流程:
1. `get_user_by_name` 查用户，`verify_password` 对比 bcrypt 哈希
2. `create_access_token` 生成 JWT — payload: `{"sub": str(user.id), "exp": ...}`
3. 返回 `{"access_token": "...", "token_type": "bearer"}`

### GET /api/v1/users/me

[app/api/v1/users.py:10](app/api/v1/users.py#L10)

请求头: `Authorization: Bearer <token>`

流程:
1. `get_current_user` 依赖注入 → OAuth2PasswordBearer 从 Authorization 头提取 token
2. `decode_access_token` → 提取 `sub` (user_id)
3. `get_user_by_id` 查库，返回 UserOut

## 认证机制

Token 生成 ([app/core/security.py:40](app/core/security.py#L40)):
```
jwt.encode({"sub": user_id, "exp": datetime}, SECRET_KEY, algorithm="HS256")
```

Token 解码 ([app/core/security.py:72](app/core/security.py#L72)):
```
jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

依赖注入链:
```
OAuth2PasswordBearer → decode_access_token → get_user_by_id → 注入路由
```

配置项 ([app/core/config.py](app/core/config.py)):
- `SECRET_KEY` / `ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` — 从 `.env` 读取，有默认值

## 数据库

[app/core/database.py](app/core/database.py)

- 引擎: `create_async_engine(mysql+aiomysql://, echo=True, pool_pre_ping=True)`
- 会话: `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`
- 会话注入: `get_db()` 异步生成器 → `Depends(get_db)`
- 建表: lifespan 启动事件调用 `init_db()` → `Base.metadata.drop_all` 再 `create_all`（开发环境每次重启重建库）

ORM 基类: `Base = declarative_base()`

## 模型

### User ([app/models/user.py](app/models/user.py))

| 列 | 类型 | 约束 |
|---|---|---|
| id | int | PK, index |
| name | String(50) | unique, index, not null |
| phone | String(20) | unique, index, not null |
| hashed_password | String(255) | not null |
| role | String(20) | default "user" |
| created_at | DateTime | server_default=func.now() |

### Question / Paper / ExamRecord

模型已定义在 `app/models/`，含 JSON 字段、枚举、外键，对应的 schemas/crud/api 尚未实现。

- [question.py](app/models/question.py) — QuestionType 枚举 (6 种题型), DifficultyLevel 枚举 (3 级), content JSON 字段
- [paper.py](app/models/paper.py) — question_ids JSON 数组, config JSON 对象, 统计字段
- [exam_record.py](app/models/exam_record.py) — answers JSON, result JSON, status 状态机 (in_progress → submitted → graded)

## 辅助脚本

- `reset_db.py` — `drop_all` + `create_all`，需输入 yes 确认
- `test_auth.py` — requests 脚本，覆盖注册/登录/查信息/重复注册/错误密码/无效token/无token/token隔离共 8 个用例
