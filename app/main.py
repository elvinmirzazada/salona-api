from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.core.config import settings
from app.api.api_v1.api import api_router
from starlette.middleware.cors import CORSMiddleware
from app.core.redis_client import publish_event
import os
import redis.asyncio as redis


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS settings
origins = [
    "http://0.0.0.0:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://0.0.0.0:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://192.168.8.5:3001",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8010",
    "http://127.0.0.1:8010",
    "http://0.0.0.0:8010",
    "https://salona.me",
    "https://www.salona.me",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "*"  # Added CSRF token header
    ],
    expose_headers=["*"],
    max_age=600  # Cache preflight requests for 10 minutes
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    publish_event("booking_created", 'testing 123')
    return {"message": "Welcome to Salona Business API"}


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHANNELS = os.getenv("REDIS_CHANNELS", "dev,booking_created").split(",")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


async def redis_subscriber(websocket: WebSocket, channels: list[str]):
    pubsub = redis_client.pubsub()
    # Unpack the list when subscribing
    await pubsub.subscribe(*channels)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(f"{message['data']}")
    except Exception as e:
        print("Subscriber error:", e)
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.close()
        await websocket.close()

# @app.websocket("/live-ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     # Pass your list of channels
#     try:
#         await redis_subscriber(websocket, CHANNELS)
#     except Exception as e:
#         print("WebSocket closed:", e)
#     finally:
#         await websocket.close()
#
@app.websocket("/live-ws")
async def websocket_test(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(*CHANNELS)
            print(f"Subscribed to Redis channel: {CHANNELS}")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    print(f"Received message: {message['data']}")
                    await websocket.send_text(message["data"])
        except WebSocketDisconnect:
            print("WebSocket disconnected")
        except Exception as e:
            print(f"WebSocket error: {str(e)}")
        finally:
            try:
                await pubsub.unsubscribe(*CHANNELS)
                await pubsub.close()
                await r.close()
                print("Redis connection closed")
            except Exception as e:
                print(f"Error closing Redis connection: {str(e)}")
