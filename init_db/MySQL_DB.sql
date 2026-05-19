-- =============================================
-- 1. 创建数据库（请根据实际环境修改字符集与排序规则）
-- =============================================
CREATE DATABASE IF NOT EXISTS student_exam_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE student_exam_system;

-- =============================================
-- 2. 用户表
-- =============================================
CREATE TABLE users (
    id              CHAR(36)     NOT NULL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    phone           VARCHAR(20)  NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(10)  NOT NULL CHECK (role IN ('student', 'teacher')),
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB;

COMMENT ON TABLE  users IS '系统用户（学生/教师）';
COMMENT ON COLUMN users.name IS '真实姓名或昵称';
COMMENT ON COLUMN users.role IS '角色：student 或 teacher';

-- 索引
CREATE INDEX idx_users_role ON users(role);

-- UUID 生成触发器
DELIMITER //
CREATE TRIGGER trg_users_before_insert
BEFORE INSERT ON users
FOR EACH ROW
BEGIN
    IF NEW.id IS NULL THEN
        SET NEW.id = UUID();
    END IF;
END//
DELIMITER ;

-- =============================================
-- 3. 题目表
-- =============================================
CREATE TABLE questions (
    id          CHAR(36)     NOT NULL PRIMARY KEY,
    type        VARCHAR(20)  NOT NULL CHECK (type IN ('choice','multi_choice','short_answer','true_false')),
    content     JSON         NOT NULL,
    -- content 结构示例：
    -- {
    --   "stem": "题目题干",
    --   "options": ["A. 选项1", "B. 选项2"],
    --   "answer": "A",
    --   "true_answer": true,
    --   "reference_answer": "参考答案",
    --   "analysis": "解析",
    --   "knowledge_point": "知识点",
    --   "difficulty": 3
    -- }
    subject     VARCHAR(50)  DEFAULT NULL,
    created_by  CHAR(36)     NOT NULL,
    is_deleted  TINYINT(1)   NOT NULL DEFAULT 0,
    created_at  DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at  DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    CONSTRAINT fk_questions_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

COMMENT ON TABLE  questions IS '题库';
COMMENT ON COLUMN questions.content IS '完整题目内容，使用 JSON 灵活存储';

-- UUID 触发器
DELIMITER //
CREATE TRIGGER trg_questions_before_insert
BEFORE INSERT ON questions
FOR EACH ROW
BEGIN
    IF NEW.id IS NULL THEN
        SET NEW.id = UUID();
    END IF;
END//
DELIMITER ;

-- 索引
CREATE INDEX idx_questions_type ON questions(type);
CREATE INDEX idx_questions_created_by ON questions(created_by);
-- 为 JSON 中的知识点创建虚拟列并索引，用于快速查询
ALTER TABLE questions ADD knowledge_point_virtual VARCHAR(100)
    AS (JSON_UNQUOTE(JSON_EXTRACT(content, '$.knowledge_point'))) VIRTUAL;
CREATE INDEX idx_questions_knowledge_point ON questions(knowledge_point_virtual);

-- =============================================
-- 4. 试卷表
-- =============================================
CREATE TABLE papers (
    id              CHAR(36)     NOT NULL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    subject         VARCHAR(50)  DEFAULT NULL,
    total_score     INT          NOT NULL DEFAULT 0,
    question_ids    JSON         NOT NULL,
    -- question_ids 示例：
    -- [
    --   {"question_id": "uuid", "score": 5, "order": 1},
    --   {"question_id": "uuid", "score": 10, "order": 2}
    -- ]
    duration_minutes INT         DEFAULT NULL,
    status          VARCHAR(20)  NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
    created_by      CHAR(36)     NOT NULL,
    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    CONSTRAINT fk_papers_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

COMMENT ON TABLE  papers IS '试卷';
COMMENT ON COLUMN papers.question_ids IS '包含题目ID、分值、顺序的数组';

-- UUID 触发器
DELIMITER //
CREATE TRIGGER trg_papers_before_insert
BEFORE INSERT ON papers
FOR EACH ROW
BEGIN
    IF NEW.id IS NULL THEN
        SET NEW.id = UUID();
    END IF;
END//
DELIMITER ;

CREATE INDEX idx_papers_status ON papers(status);
CREATE INDEX idx_papers_created_by ON papers(created_by);

-- =============================================
-- 5. 考试记录表
-- =============================================
CREATE TABLE exam_records (
    id          CHAR(36)     NOT NULL PRIMARY KEY,
    student_id  CHAR(36)     NOT NULL,
    paper_id    CHAR(36)     NOT NULL,
    answers     JSON         NOT NULL,
    -- answers 结构示例：
    -- {
    --   "qid1": "A",
    --   "qid2": "学生简答...",
    --   "qid3": true
    -- }
    score       DECIMAL(5,1) DEFAULT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','submitted','graded')),
    start_time  DATETIME(3)  DEFAULT NULL,
    submit_time DATETIME(3)  DEFAULT NULL,
    created_at  DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    CONSTRAINT fk_exam_records_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_records_paper   FOREIGN KEY (paper_id)   REFERENCES papers(id) ON DELETE CASCADE
) ENGINE=InnoDB;

COMMENT ON TABLE  exam_records IS '学生考试记录';
COMMENT ON COLUMN exam_records.answers IS '学生作答内容（键为题目ID，值为答案）';

-- UUID 触发器
DELIMITER //
CREATE TRIGGER trg_exam_records_before_insert
BEFORE INSERT ON exam_records
FOR EACH ROW
BEGIN
    IF NEW.id IS NULL THEN
        SET NEW.id = UUID();
    END IF;
END//
DELIMITER ;

-- 注意：MySQL 不支持部分唯一索引，业务上需在应用层保证“同一学生同一试卷最多只有一条进行中记录”
-- 此处添加一个普通唯一索引，但会限制已完成记录，故改用应用逻辑控制，仅建普通索引加速查询
CREATE INDEX idx_exam_records_student_paper ON exam_records(student_id, paper_id);
CREATE INDEX idx_exam_records_paper ON exam_records(paper_id);
CREATE INDEX idx_exam_records_student ON exam_records(student_id);

-- =============================================
-- 6. 批量导入批次表（AI 题目收集预览用）
-- =============================================
CREATE TABLE import_batches (
    id             CHAR(36)    NOT NULL PRIMARY KEY,
    teacher_id     CHAR(36)    NOT NULL,
    original_file  VARCHAR(500) NOT NULL,
    questions_json JSON        NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','confirmed','cancelled')),
    confirmed_ids  JSON        DEFAULT NULL,   -- 存储确认导入的题目索引数组，如 [0,1,3]
    created_at     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    CONSTRAINT fk_import_batches_teacher FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

COMMENT ON TABLE  import_batches IS 'AI 批量导入题目的临时预览批次';
COMMENT ON COLUMN import_batches.questions_json IS 'AI 解析的完整题目列表，教师预览后选择入库';

DELIMITER //
CREATE TRIGGER trg_import_batches_before_insert
BEFORE INSERT ON import_batches
FOR EACH ROW
BEGIN
    IF NEW.id IS NULL THEN
        SET NEW.id = UUID();
    END IF;
END//
DELIMITER ;

-- =============================================
-- 7. AI 异步任务表（纸质试卷电子化等长任务）
-- =============================================
CREATE TABLE ai_tasks (
    id            CHAR(36)    NOT NULL PRIMARY KEY,
    task_type     VARCHAR(50) NOT NULL,
    input_params  JSON        NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed')),
    result        JSON        DEFAULT NULL,
    error_message TEXT        DEFAULT NULL,
    created_by    CHAR(36)    DEFAULT NULL,
    created_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    started_at    DATETIME(3) DEFAULT NULL,
    finished_at   DATETIME(3) DEFAULT NULL,
    CONSTRAINT fk_ai_tasks_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

COMMENT ON TABLE  ai_tasks IS 'AI 异步任务记录（电子化、批处理等）';

DELIMITER //
CREATE TRIGGER trg_ai_tasks_before_insert
BEFORE INSERT ON ai_tasks
FOR EACH ROW
BEGIN
    IF NEW.id IS NULL THEN
        SET NEW.id = UUID();
    END IF;
END//
DELIMITER ;

CREATE INDEX idx_ai_tasks_status ON ai_tasks(status);

-- =============================================
-- 8. AI 调用日志表（成本监控）
-- =============================================
CREATE TABLE ai_usage_logs (
    id                CHAR(36)       NOT NULL PRIMARY KEY,
    task_type         VARCHAR(50)    NOT NULL,
    model             VARCHAR(50)    NOT NULL,
    prompt_tokens     INT            NOT NULL DEFAULT 0,
    completion_tokens INT            NOT NULL DEFAULT 0,
    total_tokens      INT            NOT NULL DEFAULT 0,
    cost              DECIMAL(10,6)  DEFAULT 0,
    duration_ms       INT            DEFAULT NULL,
    success           TINYINT(1)     NOT NULL DEFAULT 1,
    error_detail      TEXT           DEFAULT NULL,
    requested_by      CHAR(36)       DEFAULT NULL,
    created_at        DATETIME(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    CONSTRAINT fk_ai_usage_logs_requested_by FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

COMMENT ON TABLE  ai_usage_logs IS '大模型 API 调用日志（用于成本与质量监控）';

DELIMITER //
CREATE TRIGGER trg_ai_usage_logs_before_insert
BEFORE INSERT ON ai_usage_logs
FOR EACH ROW
BEGIN
    IF NEW.id IS NULL THEN
        SET NEW.id = UUID();
    END IF;
END//
DELIMITER ;

CREATE INDEX idx_ai_usage_logs_created ON ai_usage_logs(created_at);

-- =============================================
-- 9. 清理所有触发器的分隔符设置
-- =============================================
-- (无需操作，已在上方各段定义)

-- =============================================
-- 10. 测试数据（示例，请通过应用接口创建）
-- =============================================
-- INSERT INTO users (id, name, phone, hashed_password, role) VALUES
-- (UUID(), '张老师', '13800000001', 'hashed_password_here', 'teacher');