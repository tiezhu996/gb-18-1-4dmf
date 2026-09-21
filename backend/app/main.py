from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis
from app.modules.auth.routes import router as auth_router
from app.modules.questions.routes import router as questions_router
from app.modules.knowledge.routes import router as knowledge_router
from app.modules.practice.routes import router as practice_router
from app.modules.exam.routes import router as exam_router
from app.modules.exam.service import ExamService
from app.modules.errors.routes import router as errors_router
from app.modules.analysis.routes import router as analysis_router


async def auto_settle_loop():
    """周期性把到点未交卷的考试按已保存答案自动结算。"""
    while True:
        try:
            await ExamService.auto_settle_due_exams()
        except Exception as exc:
            print(f"[exam] 自动结算任务异常: {exc}")
        await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_redis()
    try:
        await ExamService.ensure_indexes()
    except Exception as exc:
        print(f"[exam] 创建索引失败（不影响运行）: {exc}")
    task = asyncio.create_task(auto_settle_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["认证"])
app.include_router(questions_router, prefix="/api/questions", tags=["题目管理"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["知识点体系"])
app.include_router(practice_router, prefix="/api/practice", tags=["练习模式"])
app.include_router(exam_router, prefix="/api/exam", tags=["模拟考试"])
app.include_router(errors_router, prefix="/api/errors", tags=["错题本"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["学习分析"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
