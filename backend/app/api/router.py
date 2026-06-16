from fastapi import APIRouter

from app.api.routes import auth, chats, notes, tasks, users, worklogs

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(worklogs.router, prefix="/worklogs", tags=["worklogs"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
