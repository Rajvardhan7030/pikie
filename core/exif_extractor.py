import os
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS, GPSTAGS

class EXIFExtractor:
    """
    A class to extract and process EXIF metadata from image files.
    Includes comprehensive error handling for edge cases.
    """
    
    def __init__(self, image_path):
        """
        Constructor: initializes the extractor with an image file.
        
        Args:
            image_path: Path to the image file to analyze
        """
        self.image_path = image_path
        self.img = None
        self.exif_data = None
        self.processed_data = {}
        
        # Validate file exists before trying to open
        if not os.path.exists(image_path):
            self.processed_data['error'] = f"File not found: {image_path}"
            return
            
        # Check if it's actually a file (not a directory)
        if not os.path.isfile(image_path):
            self.processed_data['error'] = f"Path is not a file: {image_path}"
            return
        
        # Attempt to load the image
        self._load_image()
    
    def _load_image(self):
        """
        Private method to load the image file with specific error handling.
        """
        try:
            # Open the image using Pillow
            self.img = Image.open(self.image_path)
            
        except PermissionError:
            self.processed_data['error'] = f"Permission denied: {self.image_path}"
            
        except UnidentifiedImageError:
            self.processed_data['error'] = f"Unsupported or corrupted image format: {self.image_path}"
            
        except Exception as e:
            self.processed_data['error'] = f"Failed to load image: {str(e)}"
            
        else:
            try:
                self.exif_data = self.img._getexif()
            except Exception as e:
                self.processed_data['error'] = f"Image loaded but EXIF data is corrupted: {str(e)}"
    
    def extract_all(self):
        """
        Main public method to extract and process all EXIF data.
        
        Returns:
            dict: Processed EXIF data or error message
        """
        if 'error' in self.processed_data:
            return self.processed_data
            
        if self.exif_data is None:
            self.processed_data['error'] = "No EXIF data found in this image"
            return self.processed_data
        
        # Process standard EXIF tags
        self._process_standard_tags()
        
        # Process GPS data separately
        self._process_gps_data()
        
        return self.processed_data
    
    def _process_standard_tags(self):
        """
        Convert numeric EXIF tags to human-readable names.
        """
        for tag_id, value in self.exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            self.processed_data[tag_name] = value
    
    def _process_gps_data(self):
        """
        Extract and convert GPS coordinates with validation.
        """
        if 'GPSInfo' not in self.processed_data:
            return
        
        gps_data = self.processed_data['GPSInfo']
        
        if not isinstance(gps_data, dict):
            self.processed_data['GPSParseError'] = "GPSInfo is not in expected format"
            return
        
        TAG_NAME_TO_ID = {v: k for k, v in GPSTAGS.items()}
        
        lat_dms = gps_data.get(TAG_NAME_TO_ID.get('GPSLatitude'))
        lat_ref = gps_data.get(TAG_NAME_TO_ID.get('GPSLatitudeRef'))
        lon_dms = gps_data.get(TAG_NAME_TO_ID.get('GPSLongitude'))
        lon_ref = gps_data.get(TAG_NAME_TO_ID.get('GPSLongitudeRef'))
        
        if not all([lat_dms, lat_ref, lon_dms, lon_ref]):
            self.processed_data['GPSParseError'] = "Incomplete GPS data (missing lat/lon components)"
            return
        
        if not self._validate_dms(lat_dms) or not self._validate_dms(lon_dms):
            self.processed_data['GPSParseError'] = "Invalid DMS coordinate format"
            return
        
        try:
            latitude = self._convert_dms_to_decimal(lat_dms, lat_ref)
            longitude = self._convert_dms_to_decimal(lon_dms, lon_ref)
            
            self.processed_data['GPSLatitudeDecimal'] = latitude
            self.processed_data['GPSLongitudeDecimal'] = longitude
            
        except Exception as e:
            self.processed_data['GPSParseError'] = f"Failed to convert GPS coordinates: {str(e)}"
    
    def _validate_dms(self, dms):
        """
        Validate that DMS tuple has correct structure.
        """
        if not isinstance(dms, (tuple, list)) or len(dms) != 3:
            return False
        
        for item in dms:
            if isinstance(item, (tuple, list)):
                if len(item) != 2:
                    return False
                try:
                    if float(item[1]) == 0:
                        return False
                except (ValueError, TypeError):
                    return False
            else:
                try:
                    float(item)
                except (ValueError, TypeError):
                    return False
        
        return True
    
    def _convert_dms_to_decimal(self, dms_tuple, direction):
        """
        Convert DMS to decimal with error handling.
        """
        if isinstance(dms_tuple[0], tuple):
            degrees = dms_tuple[0][0] / dms_tuple[0][1]
            minutes = dms_tuple[1][0] / dms_tuple[1][1]
            seconds = dms_tuple[2][0] / dms_tuple[2][1]
        else:
            degrees, minutes, seconds = dms_tuple
        
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        
        if direction in ['S', 'W']:
            decimal = -decimal
            
        return decimal
