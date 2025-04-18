from contextlib import asynccontextmanager
from typing import Optional
from databases import Database
from sqlalchemy import select
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import urls
from database_manager import DatabaseManager
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
BASE_URL = os.getenv("BASE_URL")

logger.info(f"DATABASE_URL configured: {bool(DATABASE_URL)}")
logger.info(f"SUPABASE_URL configured: {bool(SUPABASE_URL)}")
logger.info(f"BASE_URL configured: {bool(BASE_URL)}")

# Initialize supabase client
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database connection when the app starts
    database = Database(DATABASE_URL)
    await database.connect()
    
    # Create database manager and attach both to app state
    app.state.database = database
    app.state.dbm = DatabaseManager(database, urls, supabase_client)
    
    logger.info("Database connected and manager initialized")
    
    yield
    
    # Clean up when the app shuts down
    await database.disconnect()
    logger.info("Database disconnected")

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
async def shorten_url(request: URLRequest, app_request: Request):
    try:
        logger.info(f"Received request to shorten: {request.original_url[:30]}...")
        
        # Get database manager from app state
        dbm = app_request.app.state.dbm
        database = app_request.app.state.database
        
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
        logger.error(f"Error in shorten_url: {str(e)}", exc_info=True)
        return {"error": str(e)}
    
@app.get("/{short_url}")
async def redirect_to_long_url(short_url: str, request: Request):
    try:
        # Get database manager from app state
        dbm = request.app.state.dbm
        
        result = await dbm.get_url(short_url) 
        if result:
            long_url = result["long_url"]
            return RedirectResponse(url=long_url)
        return {"error": "Short URL not found"}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/health")
async def health_check(request: Request):
    try:
        # Check database connection
        await request.app.state.database.fetch_one("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503