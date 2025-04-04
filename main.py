from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
from database import dbm

app = FastAPI()

class URLRequest(BaseModel):
    original_url: str
    custom_short: Optional[str] = None

@app.post("/shorten")
async def shorten_url(request: URLRequest):
    result = dbm.add_url(request.original_url, request.custom_short)
    if not result:
        result = dbm.generate_short_url()
    else:
        return {
        "original_url": request.original_url,
        "short_url": f"http://localhost:8000/{result}"
    }

@app.get("/{short_url}")
async def redirect_to_long_url(request: URLRequest):
    long_url = f"https://example.com/{request.short_url}"
    return {"long_url": long_url}