from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.data.init_data import init_sample_data

client: AsyncIOMotorClient = None
db = None


async def init_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    await init_sample_data(db)


def get_db():
    return db
