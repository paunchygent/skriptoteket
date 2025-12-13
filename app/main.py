from __future__ import annotations

from typing import Dict

import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="Utility Scripts API",
    description="A collection of utility scripts for internal use",
    version="0.1.0"
)

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint that provides basic API information."""
    return {
        "message": "Welcome to the Utility Scripts API",
        "status": "operational",
        "docs": "/docs"
    }

# Example utility endpoint
@app.get("/utils/hello/{name}")
async def say_hello(name: str) -> Dict[str, str]:
    """Example utility endpoint that greets the user."""
    return {"message": f"Hello, {name}! This is a sample utility endpoint."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
