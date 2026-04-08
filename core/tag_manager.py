import os
import json
import shutil
import piexif
from PIL import Image
from utils.validators import validate_tag_name

class TagManager:
    """
    Handles custom metadata injection (tagging system) for images.
    Uses UserComment EXIF field to store structured JSON data.
    """
    
    USER_COMMENT_TAG = 0x9286
    ENCODING_PREFIX_LEN = 8
    
    def __init__(self, image_path):
        self.image_path = image_path
        self.exif_dict = None
        self.custom_tags = {}
        self._load_exif()

    def _load_exif(self):
        """Loads EXIF data and extracts existing custom tags from UserComment."""
        try:
            # Check if it's a JPEG or TIFF for piexif
            with open(self.image_path, 'rb') as f:
                header = f.read(2)
                if header not in (b'\xff\xd8', b'II', b'MM'):
                    # Not JPEG or TIFF, piexif might fail or behave unexpectedly
                    # We'll still try to load with PIL for other formats
                    img = Image.open(self.image_path)
                    if 'exif' in img.info:
                        self.exif_dict = piexif.load(img.info['exif'])
                    else:
                        raise ValueError("No EXIF in non-JPEG file")
                else:
                    self.exif_dict = piexif.load(self.image_path)
            
            user_comment = self.exif_dict.get("Exif", {}).get(self.USER_COMMENT_TAG, b"")
            
            if len(user_comment) > self.ENCODING_PREFIX_LEN:
                prefix = user_comment[:self.ENCODING_PREFIX_LEN]
                data = user_comment[self.ENCODING_PREFIX_LEN:]
                
                comment_str = ""
                try:
                    if b'UNICODE' in prefix:
                        # Try to handle UTF-16 with possible BOM or LE/BE
                        # We'll try LE first since that's how we save it
                        try:
                            comment_str = data.decode('utf-16-le')
                        except UnicodeDecodeError:
                            comment_str = data.decode('utf-16')
                    else:
                        # Fallback to ASCII/UTF-8
                        comment_str = data.decode('ascii', errors='ignore')
                    
                    # Find first '{' to skip any stray chars
                    start = comment_str.find('{')
                    if start != -1:
                        self.custom_tags = json.loads(comment_str[start:])
                except Exception:
                    self.custom_tags = {}
        except Exception:
            # If image has no EXIF or it's corrupted, start fresh
            self.exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
            self.custom_tags = {}

    def add_tag(self, key, value, is_numeric=False):
        """Adds or updates a custom tag."""
        if not validate_tag_name(key):
            raise ValueError(f"Invalid tag name: {key}. Use alphanumeric/underscore and max 32 chars.")

        if is_numeric:
            try:
                if "." in str(value):
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                raise ValueError(f"Value '{value}' is not a valid number")
        else:
            value = str(value)
            if len(value) > 256:
                raise ValueError("Tag value exceeds 256 characters")
        
        self.custom_tags[key] = value

    def remove_tag(self, key):
        """Removes a specific custom tag."""
        if key in self.custom_tags:
            del self.custom_tags[key]
            return True
        return False

    def clear_all(self):
        """Removes all custom tags."""
        self.custom_tags = {}

    def list_tags(self):
        """Returns the dictionary of custom tags."""
        return self.custom_tags

    def save(self, output_path=None):
        """Saves the modified EXIF data back to the image."""
        if output_path is None:
            output_path = self.image_path
            # Backup original image if we are overwriting
            backup_path = self.image_path + ".backup"
            if not os.path.exists(backup_path):
                shutil.copy2(self.image_path, backup_path)

        # Prepare UserComment with JSON
        json_data = json.dumps(self.custom_tags)
        # We'll use UNICODE prefix for safety
        # Prefix must be exactly 8 bytes
        comment_bytes = b"UNICODE\x00" + json_data.encode('utf-16-le')
        
        if "Exif" not in self.exif_dict:
            self.exif_dict["Exif"] = {}
        
        self.exif_dict["Exif"][self.USER_COMMENT_TAG] = comment_bytes
        
        try:
            exif_bytes = piexif.dump(self.exif_dict)
            img = Image.open(self.image_path)
            
            # Modern Pillow handles 'exif' argument for JPEG and WebP
            # For PNG, it's slightly different but Pillow 10+ supports it.
            img.save(output_path, exif=exif_bytes)
        except Exception as e:
            raise RuntimeError(f"Failed to save image with new EXIF: {str(e)}")

    @staticmethod
    def validate_tag_name(name):
        return validate_tag_name(name)
