import redis.asyncio as redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def publish_event(channel: str, message: str):
    """Publish a message to a Redis channel."""
    await redis_client.publish(channel, message)
