import logging
import sys
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import init_db, close_db
from app.api.v1 import auth, users, questions, papers, exam_records


# 配置日志
def setup_logging():
    """配置应用日志系统"""
    # 创建logger
    logger = logging.getLogger("exam_api")
    logger.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    
    return logger


# 创建全局logger实例
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    logger.info("=" * 60)
    logger.info("[START] Application starting up...")
    logger.info(f"[TIME] Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await init_db()
    logger.info("[OK] Database initialized")
    logger.info("=" * 60)
    yield
    # 关闭事件
    logger.info("=" * 60)
    logger.info("[END] Application shutting down...")
    logger.info(f"[TIME] Shutdown time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await close_db()
    logger.info("[OK] Database connection closed")
    logger.info("=" * 60)


app = FastAPI(
    title="Question API",
    description="做题系统后端",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# 注册中间件 - 请求日志
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求"""
    start_time = datetime.now()
    
    # 记录请求信息
    logger.info(f"[REQ] Request: {request.method} {request.url.path}")
    logger.info(f"   Client: {request.client.host if request.client else 'Unknown'}")
    logger.info(f"   Headers: {dict(request.headers)}")
    
    # 处理请求
    try:
        response = await call_next(request)
        
        # 计算响应时间
        process_time = (datetime.now() - start_time).total_seconds()
        
        # 记录响应信息
        logger.info(f"[RES] Response: {response.status_code} ({process_time:.3f}s)")
        
        return response
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"[ERR] Error: {str(e)} ({process_time:.3f}s)")
        raise


# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(questions.router, prefix="/api/v1")
app.include_router(papers.router, prefix="/api/v1")
app.include_router(exam_records.router, prefix="/api/v1")


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "E-commerce API is running"}

