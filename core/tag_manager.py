import os
import json
import shutil
import piexif
from PIL import Image

class TagManager:
    """
    Handles custom metadata injection (tagging system) for images.
    Uses UserComment EXIF field to store structured JSON data.
    """
    
    USER_COMMENT_TAG = 0x9286
    
    def __init__(self, image_path):
        self.image_path = image_path
        self.exif_dict = None
        self.custom_tags = {}
        self._load_exif()

    def _load_exif(self):
        """Loads EXIF data and extracts existing custom tags from UserComment."""
        try:
            self.exif_dict = piexif.load(self.image_path)
            user_comment = self.exif_dict.get("Exif", {}).get(self.USER_COMMENT_TAG, b"")
            
            # UserComment in piexif can be prefixed with encoding (e.g., ASCII, UNICODE)
            # Standard: first 8 bytes are encoding. We'll try to handle it.
            if len(user_comment) > 8:
                # Common prefixes: b'ASCII\x00\x00\x00', b'UNICODE\x00'
                # We'll just try to find the JSON part.
                comment_str = ""
                try:
                    # Try to decode the whole thing and find JSON
                    decoded = user_comment.decode('utf-16' if b'UNICODE' in user_comment[:8] else 'ascii', errors='ignore')
                    # Find first '{'
                    start = decoded.find('{')
                    if start != -1:
                        comment_str = decoded[start:]
                except:
                    pass
                
                if comment_str:
                    try:
                        self.custom_tags = json.loads(comment_str)
                    except json.JSONDecodeError:
                        self.custom_tags = {}
        except Exception:
            # If image has no EXIF or it's corrupted, start fresh
            self.exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
            self.custom_tags = {}

    def add_tag(self, key, value, is_numeric=False):
        """Adds or updates a custom tag."""
        if len(key) > 32:
            raise ValueError("Tag name exceeds 32 characters")
        
        if not key.isalnum() and "_" not in key:
            raise ValueError("Invalid tag name. Use alphanumeric and underscore only.")

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
        comment_bytes = b"UNICODE\x00" + json_data.encode('utf-16-le')
        
        if "Exif" not in self.exif_dict:
            self.exif_dict["Exif"] = {}
        
        self.exif_dict["Exif"][self.USER_COMMENT_TAG] = comment_bytes
        
        exif_bytes = piexif.dump(self.exif_dict)
        
        try:
            # We use PIL to save because piexif.insert only works for JPEG/TIFF
            img = Image.open(self.image_path)
            img.save(output_path, exif=exif_bytes)
        except Exception as e:
            raise RuntimeError(f"Failed to save image with new EXIF: {str(e)}")

    @staticmethod
    def validate_tag_name(name):
        return len(name) <= 32 and (name.isalnum() or "_" in name)
