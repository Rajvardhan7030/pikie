import argparse
import sys
import os
import json
import getpass
from core.exif_extractor import EXIFExtractor
from core.tag_manager import TagManager
from core.crypto_engine import CryptoEngine
from utils.validators import validate_password

def handle_extract(args):
    extractor = EXIFExtractor(args.image_path)
    data = extractor.extract_all()
    
    if 'error' in data:
        print(f"Error: {data['error']}", file=sys.stderr)
        return 1
    
    if args.all:
        print("ALL EXIF TAGS:")
        print("-" * 60)
        for key in sorted(data.keys()):
            value = data[key]
            if isinstance(value, (bytes, str)) and len(str(value)) > 80:
                value = str(value)[:77] + "..."
            print(f"{key}: {value}")
        print("-" * 60)
        print(f"Total tags: {len(data)}")
        
    elif args.format == "json":
        print(json.dumps(data, indent=2, default=str))
        
    else:
        print("EXIF Data Extracted Successfully!")
        print("-" * 50)
        print(f"Camera Make: {data.get('Make', 'N/A')}")
        print(f"Camera Model: {data.get('Model', 'N/A')}")
        print(f"Date Taken: {data.get('DateTime', 'N/A')}")
        
        if 'GPSLatitudeDecimal' in data:
            print(f"Latitude: {data['GPSLatitudeDecimal']}")
            print(f"Longitude: {data['GPSLongitudeDecimal']}")
        elif 'GPSParseError' in data:
            print(f"GPS Error: {data['GPSParseError']}")
        else:
            print("No GPS data in this image")
        
        print("-" * 50)
        print(f"Total tags extracted: {len(data)}")
    return 0

def handle_tag(args):
    try:
        tm = TagManager(args.image_path)
        
        if args.clear_all:
            tm.clear_all()
            print("All custom tags cleared.")
        
        if args.remove:
            for key in args.remove:
                if tm.remove_tag(key):
                    print(f"Removed tag: {key}")
                else:
                    print(f"Tag not found: {key}")
        
        if args.file:
            with open(args.file, 'r') as f:
                tags = json.load(f)
                for k, v in tags.items():
                    tm.add_tag(k, v)
                    print(f"Added tag from file: {k}={v}")

        if args.add:
            for item in args.add:
                if "=" not in item:
                    print(f"Invalid tag format: {item}. Use key=value or key:number=value")
                    continue
                
                key_part, value = item.split("=", 1)
                is_numeric = False
                if ":number" in key_part:
                    key = key_part.replace(":number", "")
                    is_numeric = True
                else:
                    key = key_part
                
                try:
                    tm.add_tag(key, value, is_numeric=is_numeric)
                    print(f"Added tag: {key}={value}")
                except ValueError as e:
                    print(f"Error adding tag '{key}': {str(e)}")

        if args.list:
            tags = tm.list_tags()
            if not tags:
                print("No custom tags found.")
            else:
                print("Custom Tags:")
                for k, v in tags.items():
                    print(f"  {k}: {v}")
        
        if args.add or args.remove or args.clear_all or args.file:
            tm.save()
            print("Changes saved successfully.")
        return 0
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

def handle_encrypt(args):
    password = args.password
    if not password:
        if args.password_file:
            with open(args.password_file, 'r') as f:
                password = f.read().strip()
        else:
            password = getpass.getpass("Enter password for encryption: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Passwords do not match!")
                return 1

    valid, msg = validate_password(password)
    if not valid:
        print(f"Warning: {msg}")

    try:
        engine = CryptoEngine(password)
        output = args.output or (os.path.splitext(args.image_path)[0] + ".pikie")
        engine.encrypt(args.image_path, output, mode=args.mode)
        print(f"Encryption successful. Saved to: {output}")
        return 0
    except Exception as e:
        print(f"Encryption failed: {str(e)}", file=sys.stderr)
        return 1

def handle_decrypt(args):
    password = args.password
    if not password:
        password = getpass.getpass("Enter password for decryption: ")

    try:
        engine = CryptoEngine(password)
        
        if args.metadata:
            meta = engine.get_metadata(args.image_path)
            print("Encrypted File Metadata:")
            print(json.dumps(meta, indent=2))
            return 0

        if args.verify_only:
            engine.decrypt(args.image_path) # Just check password
            print("Password verified successfully.")
            return 0

        output = args.output
        orig_ext, _ = engine.decrypt(args.image_path, output)
        if not output:
            output = os.path.splitext(args.image_path)[0] + "_restored" + orig_ext
            engine.decrypt(args.image_path, output)
            
        print(f"Decryption successful. Saved to: {output}")
        return 0
    except Exception as e:
        print(f"Decryption failed: {str(e)}", file=sys.stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(description="Pikie - EXIF Metadata & Privacy Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Extract command (also default)
    extract_parser = subparsers.add_parser("extract", help="Extract EXIF metadata")
    extract_parser.add_argument("image_path", help="Path to the image file")
    extract_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    extract_parser.add_argument("--all", action="store_true", help="Show all tags")

    # Tag command
    tag_parser = subparsers.add_parser("tag", help="Custom metadata tagging")
    tag_parser.add_argument("image_path", help="Path to the image file")
    tag_parser.add_argument("--add", action="append", help="Add tag 'key=value' or 'key:number=value'")
    tag_parser.add_argument("--file", help="Load tags from JSON file")
    tag_parser.add_argument("--remove", action="append", help="Remove specific tag")
    tag_parser.add_argument("--clear-all", action="store_true", help="Remove all custom tags")
    tag_parser.add_argument("--list", action="store_true", help="List existing custom tags")

    # Encrypt command
    enc_parser = subparsers.add_parser("encrypt", help="Encrypt image")
    enc_parser.add_argument("image_path", help="Path to the image file")
    enc_parser.add_argument("--output", help="Output .pikie file path")
    enc_parser.add_argument("--password", help="Password (insecure, use prompt)")
    enc_parser.add_argument("--password-file", help="Read password from file")
    enc_parser.add_argument("--mode", choices=["full", "exif-preserve"], default="full", help="Encryption mode")

    # Decrypt command
    dec_parser = subparsers.add_parser("decrypt", help="Decrypt image")
    dec_parser.add_argument("image_path", help="Path to the .pikie file")
    dec_parser.add_argument("--output", help="Output image file path")
    dec_parser.add_argument("--password", help="Password")
    dec_parser.add_argument("--verify-only", action="store_true", help="Verify password only")
    dec_parser.add_argument("--metadata", action="store_true", help="Show metadata only")

    # Handle legacy behavior: if first arg is a file and not a command
    if len(sys.argv) > 1 and sys.argv[1] not in subparsers.choices and not sys.argv[1].startswith('-'):
        # Assume 'extract' command
        sys.argv.insert(1, 'extract')

    args = parser.parse_args()

    if args.command == "extract":
        return handle_extract(args)
    elif args.command == "tag":
        return handle_tag(args)
    elif args.command == "encrypt":
        return handle_encrypt(args)
    elif args.command == "decrypt":
        return handle_decrypt(args)
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
