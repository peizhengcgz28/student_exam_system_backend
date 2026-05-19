-- =============================================
-- 1. 创建数据库（在 PostgreSQL 中执行）
-- =============================================
-- CREATE DATABASE student_exam_system;
-- \c student_exam_system;

-- =============================================
-- 2. 扩展与基础配置
-- =============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- 生成 UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- 密码哈希（可选，也可后端处理）

-- =============================================
-- 3. 用户表
-- =============================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(100)  NOT NULL,
    phone           VARCHAR(20)   NOT NULL UNIQUE,
    hashed_password VARCHAR(255)  NOT NULL,
    role            VARCHAR(10)   NOT NULL CHECK (role IN ('student', 'teacher')),
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  users IS '系统用户（学生/教师）';
COMMENT ON COLUMN users.name IS '真实姓名或昵称';
COMMENT ON COLUMN users.role IS '角色：student 或 teacher';

-- 角色索引（登录时快速查找）
CREATE INDEX idx_users_role ON users(role);

-- =============================================
-- 4. 题目表
-- =============================================
CREATE TABLE questions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type            VARCHAR(20)   NOT NULL CHECK (type IN ('choice', 'multi_choice', 'short_answer', 'true_false')),
    content         JSONB         NOT NULL,
    -- content 结构示例:
    -- {
    --   "stem": "题目题干",
    --   "options": ["A. 选项1", "B. 选项2", ...],
    --   "answer": "A",               -- 选择题正确选项字母(多选用数组)
    --   "true_answer": true,         -- 判断题用
    --   "reference_answer": "...",   -- 简答题参考答案
    --   "analysis": "题目解析",
    --   "knowledge_point": "知识点",
    --   "difficulty": 3              -- 1~5
    -- }
    subject         VARCHAR(50)   DEFAULT NULL,        -- 学科
    created_by      UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_deleted      BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  questions IS '题库';
COMMENT ON COLUMN questions.content IS '完整题目内容，使用 JSONB 灵活存储';

-- 提高查询性能
CREATE INDEX idx_questions_type ON questions(type) WHERE is_deleted = FALSE;
CREATE INDEX idx_questions_created_by ON questions(created_by);
CREATE INDEX idx_questions_content_gin ON questions USING gin(content jsonb_path_ops); -- 用于 JSONB 内字段查询（如知识点）

-- =============================================
-- 5. 试卷表
-- =============================================
CREATE TABLE papers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(200)  NOT NULL,
    subject         VARCHAR(50)   DEFAULT NULL,
    total_score     INT           NOT NULL DEFAULT 0,
    question_ids    JSONB         NOT NULL DEFAULT '[]',
    -- question_ids 示例:
    -- [
    --   {"question_id": "uuid", "score": 5, "order": 1},
    --   {"question_id": "uuid", "score": 10, "order": 2}
    -- ]
    duration_minutes INT          DEFAULT NULL,        -- 考试时长（分钟）
    status          VARCHAR(20)   NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    created_by      UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  papers IS '试卷';
COMMENT ON COLUMN papers.question_ids IS '包含题目ID、分值、顺序的数组';

CREATE INDEX idx_papers_status ON papers(status);
CREATE INDEX idx_papers_created_by ON papers(created_by);

-- =============================================
-- 6. 考试记录表
-- =============================================
CREATE TABLE exam_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id      UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paper_id        UUID          NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    answers         JSONB         NOT NULL DEFAULT '{}',
    -- answers 结构示例:
    -- {
    --   "question_id_1": "A",
    --   "question_id_2": "学生简答文本...",
    --   "question_id_3": true
    -- }
    score           DECIMAL(5,1)  DEFAULT NULL,        -- 总分（自动评分后填入）
    status          VARCHAR(20)   NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'submitted', 'graded')),
    start_time      TIMESTAMPTZ   DEFAULT NULL,
    submit_time     TIMESTAMPTZ   DEFAULT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  exam_records IS '学生考试记录';
COMMENT ON COLUMN exam_records.answers IS '学生作答内容（键为题目ID，值为答案）';

-- 一个学生同一个试卷只能有一条进行中的记录（唯一约束，但可多条已完成）
CREATE UNIQUE INDEX idx_exam_records_active ON exam_records (student_id, paper_id) WHERE status = 'in_progress';
CREATE INDEX idx_exam_records_paper ON exam_records(paper_id);
CREATE INDEX idx_exam_records_student ON exam_records(student_id);

-- =============================================
-- 7. 批量导入批次表（AI 题目收集预览用）
-- =============================================
CREATE TABLE import_batches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id      UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_file   VARCHAR(500)  NOT NULL,            -- 原始文件名或路径
    questions_json  JSONB         NOT NULL DEFAULT '[]', -- AI 解析出的题目列表
    status          VARCHAR(20)   NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    confirmed_ids   UUID[]        DEFAULT '{}',        -- 教师确认导入的题目索引（对应 questions_json 数组下标）
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  import_batches IS 'AI 批量导入题目的临时预览批次';
COMMENT ON COLUMN import_batches.questions_json IS 'AI 解析的完整题目列表，教师预览后选择入库';

-- =============================================
-- 8. AI 异步任务表（纸质试卷电子化等长任务）
-- =============================================
CREATE TABLE ai_tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type       VARCHAR(50)   NOT NULL,            -- e.g., 'digitize_paper', 'collect_questions'
    input_params    JSONB         NOT NULL DEFAULT '{}', -- 任务输入（文件路径等）
    status          VARCHAR(20)   NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    result          JSONB         DEFAULT NULL,        -- 任务结果（坐标、题目列表等）
    error_message   TEXT          DEFAULT NULL,
    created_by      UUID          REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ   DEFAULT NULL,
    finished_at     TIMESTAMPTZ   DEFAULT NULL
);

COMMENT ON TABLE  ai_tasks IS 'AI 异步任务记录（电子化、批处理等）';
CREATE INDEX idx_ai_tasks_status ON ai_tasks(status);

-- =============================================
-- 9. AI 调用日志表（成本监控）
-- =============================================
CREATE TABLE ai_usage_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type       VARCHAR(50)   NOT NULL,            -- 任务类型，关联 ai_tasks.task_type
    model           VARCHAR(50)   NOT NULL,            -- 使用的模型名称
    prompt_tokens   INT           NOT NULL DEFAULT 0,
    completion_tokens INT         NOT NULL DEFAULT 0,
    total_tokens    INT           NOT NULL DEFAULT 0,
    cost            DECIMAL(10,6) DEFAULT 0,           -- 预估费用（美元）
    duration_ms     INT,                               -- 调用耗时（毫秒）
    success         BOOLEAN       NOT NULL DEFAULT TRUE,
    error_detail    TEXT          DEFAULT NULL,
    requested_by    UUID          REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  ai_usage_logs IS '大模型 API 调用日志（用于成本与质量监控）';
CREATE INDEX idx_ai_usage_logs_created ON ai_usage_logs(created_at);

-- =============================================
-- 10. 自动更新 updated_at 的触发器函数
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要 updated_at 的表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_questions_updated_at BEFORE UPDATE ON questions FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_papers_updated_at BEFORE UPDATE ON papers FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_import_batches_updated_at BEFORE UPDATE ON import_batches FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- =============================================
-- 11. 插入一些默认测试数据（可选）
-- =============================================
-- 插入测试教师（密码为 'teacher123' 的哈希，需配合后端实际加密方式，这里仅占位）
-- INSERT INTO users (name, phone, hashed_password, role) VALUES
-- ('张老师', '13800000001', '$2b$12$...', 'teacher');
-- 实际请通过后端注册接口创建用户。