"""Main FastAPI application module."""
from fastapi import FastAPI

from src.config.settings import settings

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)


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
