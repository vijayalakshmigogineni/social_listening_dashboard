from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import pipeline, posts, stats

app = FastAPI(title="ProbePS Social Listening Dashboard API", version="0.1.0")

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
