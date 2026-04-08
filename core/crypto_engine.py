import os
import struct
import io
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

class CryptoEngine:
    """
    Handles image encryption and decryption using AES-256-GCM.
    Key derivation via PBKDF2-HMAC-SHA256.
    """
    
    MAGIC_BYTES = b"PIKIEENC"
    VERSION = 1
    SALT_SIZE = 32
    NONCE_SIZE = 12
    TAG_SIZE = 16
    PBKDF2_ITERATIONS = 100000
    
    # Header format: magic(8s), version(B), salt(32s), nonce(12s), ext(4s)
    # Using '<' for little-endian to be consistent across platforms
    HEADER_FMT = "<8sB32s12s4s"
    HEADER_SIZE = struct.calcsize(HEADER_FMT)

    def __init__(self, password):
        self.password = password.encode() if isinstance(password, str) else password

    def _derive_key(self, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
        )
        return kdf.derive(self.password)

    def encrypt(self, input_path, output_path, mode="full"):
        """
        Encrypts an image file.
        Mode: 'full' (entire file).
        """
        with open(input_path, 'rb') as f:
            data = f.read()

        # Generate salt and nonce
        salt = os.urandom(self.SALT_SIZE)
        nonce = os.urandom(self.NONCE_SIZE)
        
        # Derive key
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        
        # Encrypt
        ciphertext_with_tag = aesgcm.encrypt(nonce, data, None)
        
        # Original extension (up to 4 bytes)
        ext = os.path.splitext(input_path)[1].lower()
        ext_bytes = ext.encode().ljust(4, b'\x00')[:4]
        
        # Build header
        header = struct.pack(
            self.HEADER_FMT,
            self.MAGIC_BYTES,
            self.VERSION,
            salt,
            nonce,
            ext_bytes
        )
        
        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(ciphertext_with_tag)

    def decrypt(self, input_path, output_path=None):
        """
        Decrypts a .pikie file.
        Returns the original extension and data.
        """
        with open(input_path, 'rb') as f:
            header_data = f.read(self.HEADER_SIZE)
            if len(header_data) < self.HEADER_SIZE:
                raise ValueError("Invalid .pikie file: Header too short")
            
            magic, version, salt, nonce, ext_bytes = struct.unpack(
                self.HEADER_FMT,
                header_data
            )
            
            if magic != self.MAGIC_BYTES:
                raise ValueError("Invalid .pikie file: Magic bytes mismatch")
            
            if version != self.VERSION:
                raise ValueError(f"Unsupported version: {version}")
            
            ciphertext_with_tag = f.read()

        # Derive key
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        
        try:
            # Decrypt (tag is at the end of ciphertext_with_tag)
            decrypted_data = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        except InvalidTag:
            raise ValueError("Decryption failed: Wrong password or corrupted data")

        orig_ext = ext_bytes.rstrip(b'\x00').decode()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
        
        return orig_ext, decrypted_data

    @staticmethod
    def get_metadata(input_path):
        """Returns metadata from .pikie file without decrypting."""
        with open(input_path, 'rb') as f:
            header_data = f.read(CryptoEngine.HEADER_SIZE)
            if len(header_data) < CryptoEngine.HEADER_SIZE:
                raise ValueError("Invalid .pikie file: Header too short")
            
            magic, version, salt, nonce, ext_bytes = struct.unpack(
                CryptoEngine.HEADER_FMT,
                header_data
            )
            
            if magic != CryptoEngine.MAGIC_BYTES:
                raise ValueError("Not a .pikie file")
            
            return {
                "version": version,
                "original_extension": ext_bytes.rstrip(b'\x00').decode(),
                "salt_hex": salt.hex(),
                "nonce_hex": nonce.hex()
            }
