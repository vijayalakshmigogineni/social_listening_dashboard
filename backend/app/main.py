from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analysis, collection, pipeline, posts, stats
from app.db import models  # noqa: F401  (registers the models on Base.metadata)
from app.db.base import Base, engine
from app.services.jobs import mark_interrupted_jobs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Creates only tables that do not exist yet (the job/checkpoint tables on
    # an existing database); never alters or drops existing ones.
    Base.metadata.create_all(engine)
    mark_interrupted_jobs()
    yield


app = FastAPI(title="ProbePS Social Listening Dashboard API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(collection.router, prefix="/api/collection", tags=["collection"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
