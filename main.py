from typing import Optional
from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import dbm

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class URLRequest(BaseModel):
    original_url: str
    custom_short: Optional[str] = None

@app.get("/")
async def serve_homepage():
    return FileResponse("static/index.html")

@app.post("/shorten")
async def shorten_url(request: URLRequest):
    result = dbm.add_url(request.original_url, request.custom_short)
    return {
        "original_url": request.original_url,
        "short_url": f"http://localhost:8000/{result}"
    }

@app.get("/{short_url}")
async def redirect_to_long_url(short_url: str):
    long_url = dbm.get_url(short_url)
    return RedirectResponse(url=long_url)