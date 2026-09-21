try:
    import aioredis
except (ImportError, TypeError):
    aioredis = None

from app.core.config import settings

redis = None


async def init_redis():
    global redis
    if aioredis is None:
        redis = None
        return
    try:
        redis = await aioredis.from_url(settings.REDIS_URL)
    except Exception:
        # Redis 不可用时降级为直连数据库，不影响核心流程
        redis = None


def get_redis():
    return redis
