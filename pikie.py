import argparse
import os  # Import os for file path operations
import sys  # Import sys for exit codes
from PIL import Image, UnidentifiedImageError  # Import specific exceptions
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
        # This provides a clearer error than PIL's generic "cannot identify"
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
        Catches different types of failures for better user feedback.
        """
        try:
            # Open the image using Pillow
            self.img = Image.open(self.image_path)
            
        except PermissionError:
            # Specific handling for permission denied
            self.processed_data['error'] = f"Permission denied: {self.image_path}"
            
        except UnidentifiedImageError:
            # PIL cannot identify this as a valid image format
            self.processed_data['error'] = f"Unsupported or corrupted image format: {self.image_path}"
            
        except Exception as e:
            # Catch-all for any other loading errors
            self.processed_data['error'] = f"Failed to load image: {str(e)}"
            
        else:
            # Only try to get EXIF if image loaded successfully
            # This prevents AttributeError on self.img being None
            try:
                self.exif_data = self.img._getexif()
            except Exception as e:
                # Some images load but have corrupted EXIF data
                self.processed_data['error'] = f"Image loaded but EXIF data is corrupted: {str(e)}"
    
    def extract_all(self):
        """
        Main public method to extract and process all EXIF data.
        
        Returns:
            dict: Processed EXIF data or error message
        """
        # If we already have an error from __init__ or _load_image, return it
        if 'error' in self.processed_data:
            return self.processed_data
            
        # Check if we have EXIF data to work with
        # Note: exif_data can be None even if image loaded (no EXIF in file)
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
        Handles incomplete or malformed GPS data gracefully.
        """
        if 'GPSInfo' not in self.processed_data:
            return
        
        gps_data = self.processed_data['GPSInfo']
        
        # Validate gps_data is actually a dictionary
        # Some cameras write GPSInfo as bytes or other types
        if not isinstance(gps_data, dict):
            self.processed_data['GPSParseError'] = "GPSInfo is not in expected format"
            return
        
        # Extract components with safe .get() to avoid KeyError
        lat_dms = gps_data.get(2)
        lat_ref = gps_data.get(1)
        lon_dms = gps_data.get(4)
        lon_ref = gps_data.get(3)
        
        # Validate all required components are present
        if not all([lat_dms, lat_ref, lon_dms, lon_ref]):
            self.processed_data['GPSParseError'] = "Incomplete GPS data (missing lat/lon components)"
            return
        
        # Validate DMS tuples have correct structure
        if not self._validate_dms(lat_dms) or not self._validate_dms(lon_dms):
            self.processed_data['GPSParseError'] = "Invalid DMS coordinate format"
            return
        
        try:
            latitude = self._convert_dms_to_decimal(lat_dms, lat_ref)
            longitude = self._convert_dms_to_decimal(lon_dms, lon_ref)
            
            self.processed_data['GPSLatitudeDecimal'] = latitude
            self.processed_data['GPSLongitudeDecimal'] = longitude
            
        except Exception as e:
            # Catch any conversion errors (division by zero, etc.)
            self.processed_data['GPSParseError'] = f"Failed to convert GPS coordinates: {str(e)}"
    
    def _validate_dms(self, dms):
        """
        Validate that DMS tuple has correct structure.
        
        Args:
            dms: Tuple to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(dms, tuple) or len(dms) != 3:
            return False
        
        # Each element should be a number or a tuple (numerator, denominator)
        for item in dms:
            if isinstance(item, tuple):
                if len(item) != 2 or item[1] == 0:  # Check for division by zero
                    return False
            elif not isinstance(item, (int, float)):
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


def main():
    """
    Main entry point with comprehensive error handling.
    """
    parser = argparse.ArgumentParser(
        description="Extract EXIF metadata from image files"
    )
    
    parser.add_argument(
        "image_path",
        help="Path to the image file to analyze"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text or json (default: text)"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all EXIF tags"
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = EXIFExtractor(args.image_path)
    data = extractor.extract_all()
    
    # Handle errors
    if 'error' in data:
        print(f"Error: {data['error']}", file=sys.stderr)  # Print errors to stderr
        return 1  # Non-zero exit code indicates failure
    
    # Output results (same as before)
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
        import json
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


if __name__ == "__main__":
    exit(main())