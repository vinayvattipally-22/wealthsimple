"""
Wealthsimple AI Tax Analyzer — FastAPI entry point.
CORS, router registration, DB init on startup, rate limiting, API key auth.
"""
import os
from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database.models import Base
from database.session import engine, init_db
from middleware.rate_limiter import limiter
from middleware.api_key import APIKeyMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables, initialize LightRAG, and start scheduler on startup."""
    await init_db()
    from services.lightrag_service import init_rag
    app.state.rag = await init_rag()
    from services.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title="Wealthsimple AI Tax Analyzer",
    description="AI-native tax document analysis and financial optimization",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter state
app.state.limiter = limiter

@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Please try again later."})

# Middleware (order matters: outermost first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)

# Routers
from routers import upload, cra, analysis, advisor, profiles, knowledge, trends, reports, auth, user, chat, action_items, simulator, stocks, stock_news

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(profiles.router, prefix="/api", tags=["profiles"])
app.include_router(cra.router, prefix="/api", tags=["cra"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(advisor.router, prefix="/api/advisor", tags=["advisor"])
app.include_router(knowledge.router, prefix="/api", tags=["knowledge"])
app.include_router(trends.router, prefix="/api", tags=["trends"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(action_items.router, prefix="/api", tags=["action_items"])
app.include_router(simulator.router, prefix="/api", tags=["simulator"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(stock_news.router, prefix="/api/stocks", tags=["stock_news"])


@app.get("/health")
def health():
    return {"status": "ok"}
