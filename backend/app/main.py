from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.core.config import settings
from app.db.models import Base
from app.db.session import make_engine, reconfigure_session
from app.db import session as db_session

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        Base.metadata.create_all(bind=db_session.engine)
    except OperationalError:
        if not settings.database_auto_fallback or settings.database_url == settings.database_fallback_url:
            raise

        fallback_engine = make_engine(settings.database_fallback_url)
        reconfigure_session(fallback_engine)
        Base.metadata.create_all(bind=db_session.engine)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_prefix)
