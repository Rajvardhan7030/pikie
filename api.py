# api.py - FastAPI web API for EXIF extraction
# Run with: uvicorn api:app --reload --host 0.0.0.0 --port 8000

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
import tempfile
import os
import shutil
import logging
import traceback  # For detailed error logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your EXIFExtractor - wrap in try/except to catch import errors
try:
    from pikie import EXIFExtractor
    logger.info("Successfully imported EXIFExtractor")
except Exception as e:
    logger.error(f"Failed to import EXIFExtractor: {str(e)}")
    logger.error(traceback.format_exc())
    # Create a placeholder that will fail gracefully
    class EXIFExtractor:
        def __init__(self, path):
            self.processed_data = {'error': f'Import error: {str(e)}'}
        def extract_all(self):
            return self.processed_data

# Create FastAPI application
app = FastAPI(
    title="EXIF Extractor API",
    description="Upload images and extract EXIF metadata",
    version="1.0.0"
)

# CORS - Must be added BEFORE any routes
# Allow all origins for development (restrict in production!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows ALL origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    try:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Add CORS headers explicitly as backup
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    except Exception as e:
        # If an error occurs, we still need to return a response with CORS headers
        logger.error(f"Error in middleware: {str(e)}")
        raise

# File size limit
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@app.post("/extract")
async def extract_exif(file: UploadFile = File(...)):
    """
    Endpoint to upload an image and extract EXIF data.
    """
    temp_file_path = None
    
    try:
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size} bytes. Max: {MAX_FILE_SIZE} bytes (10MB)"
            )
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/tiff", "image/png"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}"
            )
        
        # Create temp file
        safe_filename = os.path.basename(file.filename)
        suffix = os.path.splitext(safe_filename)[1]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_file_path = tmp.name
        
        logger.info(f"Processing: {safe_filename} ({file_size} bytes)")
        
        # Extract EXIF
        extractor = EXIFExtractor(temp_file_path)
        data = extractor.extract_all()
        
        if 'error' in data:
            logger.warning(f"Extraction error: {data['error']}")
            raise HTTPException(status_code=422, detail=data['error'])
        
        # Remove internal path from response
        data.pop('image_path', None)
        
        logger.info(f"Success: {safe_filename}")
        return JSONResponse(content=data)
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
        
    finally:
        # Always cleanup temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            logger.debug(f"Cleaned up: {temp_file_path}")

@app.get("/")
async def root():
    return {
        "message": "EXIF Extractor API",
        "endpoints": {
            "POST /extract": "Upload an image to extract EXIF data",
            "GET /docs": "Interactive API documentation"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "extractor_loaded": 'EXIFExtractor' in globals()}