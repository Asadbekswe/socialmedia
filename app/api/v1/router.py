from fastapi import APIRouter

from app.api.v1 import auth, feed, posts, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(posts.router)
api_router.include_router(feed.router)
