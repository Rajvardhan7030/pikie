# Pikie - EXIF Metadata & Privacy Tool

Pikie is a comprehensive tool for image EXIF metadata extraction, custom tagging, and privacy-focused encryption.

## 🚀 Features
- **EXIF Extraction**: Comprehensive extraction of camera make, model, datetime, and GPS decimal coordinates.
- **Custom Tagging**: Structured key-value tagging system stored in the `UserComment` field using JSON.
- **Privacy Protection**: AES-256-GCM authenticated encryption for images.
- **Dual Interface**: Fully functional CLI and a modern, tabbed web interface (FastAPI + Vanilla JS).

---

## 🏗️ Project Architecture
```text
pikie/
├── pikie.py              # CLI Entry point
├── api.py                # FastAPI routes & Static mounting
├── core/
│   ├── exif_extractor.py # Metadata extraction logic
│   ├── tag_manager.py    # Custom tagging system
│   └── crypto_engine.py  # AES-256-GCM encryption engine
├── web/
│   ├── static/app.js     # Frontend logic & API integration
│   └── templates/index.html # Web UI
└── utils/
    └── validators.py     # Input validation (passwords, tags)
```

---

## 🛠️ Installation
Install the required dependencies using pip:
```bash
pip install -r requirements.txt
```

---

## 💻 CLI Usage

### Metadata Extraction
```bash
python3 pikie.py extract photo.jpg [--format json] [--all]
```

### Custom Tagging
```bash
# Add tags (text and numeric)
python3 pikie.py tag photo.jpg --add "Event=Birthday" --add "Rating:number=5" --list

# Remove or clear tags
python3 pikie.py tag photo.jpg --remove "Event"
python3 pikie.py tag photo.jpg --clear-all
```

### Image Encryption/Decryption
```bash
# Encrypt
python3 pikie.py encrypt photo.jpg --output secure.pikie --password mypassword

# Decrypt
python3 pikie.py decrypt secure.pikie --output restored.jpg --password mypassword

# View encrypted file metadata
python3 pikie.py decrypt secure.pikie --metadata
```

---

## 🌐 Web Interface
Start the FastAPI server:
```bash
python3 -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```
Navigate to `http://localhost:8000` to access the **Extract**, **Tag Editor**, and **Privacy Tools** tabs.

---

## 🔒 Security Specifications
- **Encryption Algorithm**: AES-256-GCM (Authenticated Encryption).
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations.
- **Salt/Nonce**: 32-byte random salt and 12-byte random IV generated per file.
- **File Integrity**: Magic bytes (`PIKIEENC`) and versioning in the custom `.pikie` header.

---

## 📁 Supported Formats
- **Images**: JPEG, PNG, TIFF, WebP.
- **Encrypted**: Custom `.pikie` binary format.
- **Metadata Storage**: Structured JSON within the `UserComment` EXIF tag.
