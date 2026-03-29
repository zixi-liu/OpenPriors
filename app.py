"""
OpenPriors — Turn what you learn into what you do.

An open-source AI assistant that helps people integrate
new knowledge into daily practice.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.setup import router as setup_router
from routes.assets import router as assets_router

app = FastAPI(
    title="OpenPriors",
    description="Turn what you learn into what you do.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup_router)
app.include_router(assets_router)


@app.get("/")
async def root():
    return {
        "name": "OpenPriors",
        "version": "0.1.0",
        "tagline": "Turn what you learn into what you do.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
