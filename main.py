from contextlib import asynccontextmanager
from typing import Optional
from databases import Database
from sqlalchemy import select
from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import urls
from database_manager import DatabaseManager
import os
from supabase import create_client, Client

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
BASE_URL = os.getenv("BASE_URL")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)
print(supabase_client)

database = Database(DATABASE_URL)
dbm = DatabaseManager(database, urls, supabase_client)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    original_url: str
    custom_short: Optional[str] = None

# Route to serve homepage
@app.get("/")
async def serve_homepage():
    return FileResponse("static/index.html")

# Route to shorten URLs
@app.post("/shorten")
async def shorten_url(request: URLRequest):
    try:
        short_id = await dbm.add_url(request.original_url, request.custom_short)
        short_url = f"{BASE_URL}/{short_id}"

        # Fetch the complete record
        query = select(urls).where(urls.c.short_url == short_id)
        result = await database.fetch_one(query)
        
        if not result:
            return {"error": "Failed to retrieve URL information"}
            
        return {
            "original_url": request.original_url,
            "short_url": short_url,
            "qr_code_url": result["qr_code"]
        }
    except Exception as e:
        print(f"Error in shorten_url: {str(e)}")  # Add logging
        return {"error": str(e)}
    
@app.get("/{short_url}")
async def redirect_to_long_url(short_url: str):
    try:
        result = await dbm.get_url(short_url) 
        if result:
            long_url = result["long_url"]
            return RedirectResponse(url=long_url)
        return {"error": "Short URL not found"}
    except Exception as e:
        return {"error": str(e)}