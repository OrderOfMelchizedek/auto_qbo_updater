"""Main FastAPI application module."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.endpoints import auth
from src.api.middleware.security import setup_middleware
from src.config.logging_config import setup_logging
from src.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure application lifespan events."""
    # Startup
    setup_logging()
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Set up middleware
setup_middleware(app)

# Include routers
app.include_router(auth.router)


@app.get("/")
async def read_root():
    """Root endpoint returning welcome message."""
    return {"message": f"Welcome to {settings.APP_NAME}"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}


# The following is for illustrative purposes for local running;
# Uvicorn will typically be run by Procfile in deployment.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
