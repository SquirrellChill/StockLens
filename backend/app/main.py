import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, check_db_connection
from app.routers import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stocklens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup checks and graceful shutdown.
    """
    logger.info("Initializing StockLens Backend Foundation...")
    db_connected = check_db_connection()
    if db_connected:
        logger.info("Database connection established successfully.")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables verified.")
        except Exception as e:
            logger.warning(f"Automatic table creation encountered notice: {e}")
    else:
        logger.warning(
            "Database connection could not be established at startup. "
            "Verify DATABASE_URL in .env."
        )
    yield
    logger.info("StockLens Backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API foundation for StockLens - Inventory Management System",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS setup for Vite frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes under /api
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint to verify backend status.
    Expected response:
    {
      "status": "ok",
      "service": "StockLens API"
    }
    """
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
    }
