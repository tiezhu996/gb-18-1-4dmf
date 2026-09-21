from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis
from app.modules.auth.routes import router as auth_router
from app.modules.questions.routes import router as questions_router
from app.modules.knowledge.routes import router as knowledge_router
from app.modules.practice.routes import router as practice_router
from app.modules.exam.routes import router as exam_router
from app.modules.errors.routes import router as errors_router
from app.modules.analysis.routes import router as analysis_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_redis()
    yield


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
