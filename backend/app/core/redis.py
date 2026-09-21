import aioredis
from app.core.config import settings

redis = None


async def init_redis():
    global redis
    redis = await aioredis.from_url(settings.REDIS_URL)


def get_redis():
    return redis
