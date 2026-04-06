# Pikie - EXIF Metadata Extractor

Pikie is a simple tool to extract EXIF metadata from image files. It provides both a command-line interface and a web-based interface.

## Features
- Extract camera settings (Make, Model, Date, etc.)
- Extract GPS coordinates and convert them to decimal format
- CLI support for text and JSON output
- Web interface with image preview and map integration

## Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### CLI
Run the `pikie.py` script with the path to an image:
```bash
python3 pikie.py path/to/image.jpg
```

Options:
- `--format json`: Output data in JSON format
- `--all`: Show all available EXIF tags

### Web Interface
Start the FastAPI server:
```bash
python3 -m uvicorn api:app --reload
```
Then open `http://localhost:8000` in your browser.

## Supported Formats
- JPEG/JPG
- PNG
- TIFF
- WebP (via Pillow)
