import asyncio
from io import BytesIO
import random
import string
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import select, insert, delete
import qrcode
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database, urls_table, supabase_client):
        self.database = database
        self.urls_table = urls_table
        self.supabase = supabase_client

    def generate_short_url(self):
        chars = ''.join(random.choices(string.ascii_lowercase, k=4))
        digits = ''.join(random.choices(string.digits, k=2))
        return chars + digits

    async def generate_qr(self, long_url: str, short_id: str):
        try:
            # Generate the QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(long_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            # Upload the QR code to Supabase
            qr_url = self.upload_to_supabase(buffer, short_id)
            return qr_url
        except Exception as e:
            logger.error(f"QR generation error: {str(e)}")
            return f"https://via.placeholder.com/150?text={short_id}"

    def upload_to_supabase(self, buffer, short_id):
        try:
            bucket_name = "qr-codes" 
            file_name = f"{short_id}.png"
            
            # Convert BytesIO to bytes
            buffer.seek(0)
            file_data = buffer.read()
            
            print(f"Uploading {short_id} to Supabase bucket {bucket_name}")
            
            # Upload the bytes data
            response = self.supabase.storage.from_(bucket_name).upload(
                path=file_name,
                file=file_data,
                file_options={"content-type": "image/png"}
            )
            
            print(f"Upload response: {response}")
            
            # Check for successful upload
            if response and (hasattr(response, 'path') or (isinstance(response, dict) and 'path' in response)):
                qr_url = self.supabase.storage.from_(bucket_name).get_public_url(file_name)
                print(f"Generated URL: {qr_url}")
                return qr_url
            else:
                print(f"QR upload failed: {response}")
                return f"https://via.placeholder.com/150?text={short_id}"
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return f"https://via.placeholder.com/150?text={short_id}"
    
    async def add_url(self, long_url, custom_short: Optional[str] = None):
        if not long_url.startswith(('http://', 'https://')):
            long_url = f"https://{long_url}"
        # Check if custom short URL already exists
        if custom_short:
            query = select(self.urls_table).where(self.urls_table.c.short_url == custom_short)
            existing = await self.database.fetch_one(query)
            if existing:
                raise HTTPException(status_code=400, detail="Short URL already exists, please choose another one")
            short_url = custom_short
        else:
            short_url = self.generate_short_url()
            while True:
                query = select(self.urls_table).where(self.urls_table.c.short_url == short_url)
                existing = await self.database.fetch_one(query)
                if not existing:
                    break
                short_url = self.generate_short_url()

        # Generate a QR code and upload it to Supabase
        qr_code_url = await self.generate_qr(long_url, short_url)

        # Insert URL and QR code URL into the database
        query = insert(self.urls_table).values(
            long_url=long_url,
            short_url=short_url,
            qr_code=qr_code_url  # Store the Supabase URL for the QR code
        )
        await self.database.execute(query)
        
        return short_url
    
    async def get_url(self, short_url):
        try:
            query = select(self.urls_table).where(self.urls_table.c.short_url == short_url)
            result = await self.database.fetch_one(query)
            if result:
                return result
            else:
                raise HTTPException(status_code=404, detail="Short URL not found")
        except Exception as e:
            logger.error(f"Error retrieving URL {short_url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    async def delete_url(self, short_url):
        query = select(self.urls_table).where(self.urls_table.c.short_url == short_url)
        result = await self.database.fetch_one(query)
        if not result:
            raise HTTPException(status_code=400, detail="Short URL not found")
        else:
            delete_query = delete(self.urls_table).where(self.urls_table.c.short_url == short_url)
            await self.database.execute(delete_query)
            print(f"Short URL '{short_url}' deleted from the database")