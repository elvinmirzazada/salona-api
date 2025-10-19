import redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def publish_event(channel: str, message: str):
    """Publish a message to a Redis channel."""
    redis_client.publish(channel, message)
