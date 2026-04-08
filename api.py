from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
import json
import io
import mimetypes
from typing import List, Optional

from core.exif_extractor import EXIFExtractor
from core.tag_manager import TagManager
from core.crypto_engine import CryptoEngine
from utils.validators import validate_tag_name, validate_password

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Pikie API", version="2.0.0")

app.mount("/static", StaticFiles(directory="web/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

def sanitize_data(data):
    if isinstance(data, dict):
        return {str(k): sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [sanitize_data(v) for v in data]
    elif isinstance(data, bytes):
        try:
            return data.decode('utf-8', errors='replace')
        except:
            return data.hex()
    elif hasattr(data, '__str__') and 'IFDRational' in str(type(data)):
        try:
            return float(data)
        except:
            return str(data)
    else:
        return data

@app.post("/extract")
async def extract_exif(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    
    try:
        extractor = EXIFExtractor(temp_path)
        data = extractor.extract_all()
        if 'error' in data:
            raise HTTPException(status_code=422, detail=data['error'])
        return JSONResponse(content=sanitize_data(data))
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.post("/tags")
async def get_custom_tags(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    try:
        tm = TagManager(temp_path)
        return tm.list_tags()
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.post("/tag")
async def add_tags(
    file: UploadFile = File(...),
    tags_json: str = Form(...) # JSON string of tags
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    
    try:
        tm = TagManager(temp_path)
        tags = json.loads(tags_json)
        for k, v in tags.items():
            is_numeric = isinstance(v, (int, float))
            tm.add_tag(k, v, is_numeric=is_numeric)
        
        output_path = temp_path + "_tagged"
        tm.save(output_path)
        
        with open(output_path, "rb") as f:
            content = f.read()
        
        if os.path.exists(output_path): os.unlink(output_path)
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type="image/jpeg",
            headers={"Content-Disposition": f"attachment; filename=tagged_{file.filename}"}
        )
    finally:
        if os.path.exists(temp_path): os.unlink(temp_path)

@app.post("/encrypt")
async def encrypt_image(
    file: UploadFile = File(...),
    password: str = Form(...)
):
    valid, msg = validate_password(password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    
    enc_path = temp_path + ".pikie"
    try:
        engine = CryptoEngine(password)
        engine.encrypt(temp_path, enc_path)
        
        with open(enc_path, "rb") as f:
            content = f.read()
        
        if os.path.exists(enc_path): os.unlink(enc_path)

        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={os.path.splitext(file.filename)[0]}.pikie"}
        )
    finally:
        if os.path.exists(temp_path): os.unlink(temp_path)

def get_media_type(extension):
    if not extension:
        return "application/octet-stream"
    if not extension.startswith('.'):
        extension = '.' + extension
    mt, _ = mimetypes.guess_type(f"file{extension}")
    return mt or "application/octet-stream"

@app.post("/decrypt")
async def decrypt_image(
    file: UploadFile = File(...),
    password: str = Form(...)
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pikie") as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    try:
        engine = CryptoEngine(password)
        orig_ext, decrypted_data = engine.decrypt(temp_path)

        media_type = get_media_type(orig_ext)

        return StreamingResponse(
            io.BytesIO(decrypted_data),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=restored{orig_ext}"}
        )
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@app.get("/")
async def root():
    return FileResponse("web/templates/index.html")

@app.get("/health")
async def health():
    return {"status": "ok"}
