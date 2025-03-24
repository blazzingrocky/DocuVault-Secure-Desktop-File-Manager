from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import os
import json
import base64
from pathlib import Path

class FileEncryption:
    """Class to handle file encryption and decryption"""
    
    KEY_FILE = "encryption_key.dat"
    
    @staticmethod
    def generate_key():
        """Generate a new AES encryption key"""
        return get_random_bytes(32)  # 256-bit key
    
    @staticmethod
    def save_key(key, key_path=None):
        """Save encryption key to file"""
        if key_path is None:
            key_path = FileEncryption.KEY_FILE
            
        key_dir = os.path.dirname(key_path)
        if key_dir and not os.path.exists(key_dir):
            os.makedirs(key_dir)
            
        with open(key_path, 'wb') as f:
            f.write(key)
        
        return key_path
    
    @staticmethod
    def load_key(key_path=None):
        """Load encryption key from file"""
        if key_path is None:
            key_path = FileEncryption.KEY_FILE
            
        if not os.path.exists(key_path):
            return None
            
        with open(key_path, 'rb') as f:
            return f.read()
    
    @staticmethod
    def encrypt_file(file_path, key, remove_original=True):
        """
        Encrypt a file using AES encryption
        
        Args:
            file_path: Path to the file to encrypt
            key: Encryption key to use
            remove_original: Whether to remove the original file after encryption
            
        Returns:
            Path to the encrypted file
        """
        # Generate a nonce for this encryption
        cipher = AES.new(key, AES.MODE_EAX)
        
        # Read the file
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Encrypt the data
        ciphertext, tag = cipher.encrypt_and_digest(data)
        
        # Create encrypted filename
        encrypted_path = file_path
        
        # Write the encrypted file
        with open(encrypted_path, 'wb') as f:
            # Format: [nonce][tag][ciphertext]
            f.write(cipher.nonce)
            f.write(tag)
            f.write(ciphertext)
            
        return encrypted_path
    
    @staticmethod
    def decrypt_file(file_path, key, output_path=None):
        """
        Decrypt a file that was encrypted with AES
        
        Args:
            file_path: Path to the encrypted file
            key: Encryption key to use
            output_path: Path to write the decrypted file (if None, use temporary file)
            
        Returns:
            Path to the decrypted file
        """
        if output_path is None:
            # Create a temporary file path if not specified
            output_path = f"{file_path}.decrypted"
            
        # Read the encrypted file
        with open(file_path, 'rb') as f:
            # Format: [nonce][tag][ciphertext]
            nonce = f.read(16)
            tag = f.read(16)
            ciphertext = f.read()
        
        # Create cipher with the same nonce
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        
        # Decrypt and verify
        try:
            data = cipher.decrypt_and_verify(ciphertext, tag)
        except ValueError:
            # Authentication failed - tampering detected
            return None
        
        # Write the decrypted file
        with open(output_path, 'wb') as f:
            f.write(data)
            
        return output_path
    
    @staticmethod
    def is_file_encrypted(file_path, key):
        """Check if a file is encrypted by attempting to decrypt its header"""
        try:
            with open(file_path, 'rb') as f:
                nonce = f.read(16)
                tag = f.read(16)
                # Just read a small portion to check
                ciphertext = f.read(16)
                
            cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
            cipher.decrypt_and_verify(ciphertext, tag)
            return True
        except:
            return False
    
    @staticmethod
    def encrypt_folder(folder_path, key, recursive=True, extensions=None):
        """
        Encrypt all files in a folder
        
        Args:
            folder_path: Path to the folder
            key: Encryption key
            recursive: Whether to encrypt files in subfolders
            extensions: List of file extensions to encrypt (None for all)
            
        Returns:
            Number of files encrypted
        """
        count = 0
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip already encrypted files
                if FileEncryption.is_file_encrypted(file_path, key):
                    continue
                
                # Skip files with non-matching extensions
                if extensions and not any(file.lower().endswith(ext.lower()) for ext in extensions):
                    continue
                
                try:
                    FileEncryption.encrypt_file(file_path, key)
                    count += 1
                except Exception as e:
                    print(f"Error encrypting {file_path}: {e}")
            
            if not recursive:
                break
                
        return count
    
    @staticmethod
    def decrypt_folder(folder_path, key, recursive=True, extensions=None):
        """
        Decrypt all files in a folder
        
        Args:
            folder_path: Path to the folder
            key: Encryption key
            recursive: Whether to decrypt files in subfolders
            extensions: List of file extensions to decrypt (None for all)
            
        Returns:
            Number of files decrypted
        """
        count = 0
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip non-encrypted files
                if not FileEncryption.is_file_encrypted(file_path, key):
                    continue
                
                # Skip files with non-matching extensions
                if extensions and not any(file.lower().endswith(ext.lower()) for ext in extensions):
                    continue
                
                try:
                    FileEncryption.decrypt_file(file_path, key, file_path)
                    count += 1
                except Exception as e:
                    print(f"Error decrypting {file_path}: {e}")
            
            if not recursive:
                break
                
        return count
    
    @staticmethod
    def secure_access(file_path, key, callback):
        """
        Securely access an encrypted file by:
        1. Decrypting it
        2. Allowing access via callback
        3. Re-encrypting if needed
        
        Args:
            file_path: Path to the encrypted file
            key: Encryption key
            callback: Function to call with path to decrypted file
            
        Returns:
            Result from callback function
        """
        # Check if the file is encrypted
        is_encrypted = FileEncryption.is_file_encrypted(file_path, key)
        
        if is_encrypted:
            # Decrypt to temporary file
            temp_path = FileEncryption.decrypt_file(file_path, key)
            
            try:
                # Call the callback with the decrypted path
                result = callback(temp_path)
                
                # Re-encrypt if the file was modified
                if os.path.getmtime(temp_path) > os.path.getmtime(file_path):
                    FileEncryption.encrypt_file(temp_path, key)
                    os.replace(temp_path, file_path)
                
                # Clean up
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                return result
            except Exception as e:
                # Clean up on error
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
        else:
            # File is not encrypted, just pass it through
            return callback(file_path)
