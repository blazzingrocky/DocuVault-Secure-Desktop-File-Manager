from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from Crypto.Protocol.KDF import PBKDF2
import os
import base64
import json
import hashlib
import tempfile
import shutil

class FileEncryptor:
    def __init__(self, master_password=None):
        self.master_password = master_password
        self.key_file = os.path.join(os.path.expanduser('~'), '.docuvault_keys.json')
        self.temp_files = {}  # Track temporary decrypted files
        
    def set_master_password(self, password):
        """Set or update the master password"""
        self.master_password = password
        # Generate a new salt and store it
        salt = get_random_bytes(16)
        self.save_salt(salt)
        return True
        
    def save_salt(self, salt):
        """Save the salt to the key file"""
        data = {}
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, 'r') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        data['salt'] = base64.b64encode(salt).decode('utf-8')
        
        with open(self.key_file, 'w') as f:
            json.dump(data, f)
            
    def get_salt(self):
        """Retrieve the salt from the key file"""
        if not os.path.exists(self.key_file):
            # If no salt exists, create one
            salt = get_random_bytes(16)
            self.save_salt(salt)
            return salt
            
        try:
            with open(self.key_file, 'r') as f:
                data = json.load(f)
                salt = base64.b64decode(data.get('salt', ''))
                if not salt:
                    salt = get_random_bytes(16)
                    self.save_salt(salt)
                return salt
        except Exception as e:
            # If any error occurs, generate a new salt
            salt = get_random_bytes(16)
            self.save_salt(salt)
            return salt
            
    def derive_key(self, password=None):
        """Derive an AES key from the master password"""
        if password is None:
            password = self.master_password
            
        if not password:
            raise ValueError("No password provided for key derivation")
            
        salt = self.get_salt()
        # Use PBKDF2 to derive a 32-byte (256-bit) key
        key = PBKDF2(password.encode(), salt, dkLen=32, count=1000000)
        return key
        
    def encrypt_file(self, file_path, output_path=None, password=None):
        """
        Encrypt a file using AES-256-GCM
        
        Args:
            file_path: Path to the file to encrypt
            output_path: Path where to save the encrypted file (default: same as input with .enc extension)
            password: Optional password to use (default: master password)
            
        Returns:
            Path to the encrypted file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # If no output path specified, use the original path with .enc extension
        if output_path is None:
            output_path = file_path + '.enc'
            
        try:
            # Derive the encryption key
            key = self.derive_key(password)
            
            # Generate a random nonce
            nonce = get_random_bytes(16)
            
            # Create cipher
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            
            # Read the file
            with open(file_path, 'rb') as f:
                plaintext = f.read()
                
            # Encrypt the data
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)
            
            # Write the encrypted file
            with open(output_path, 'wb') as f:
                # Format: nonce (16 bytes) + tag (16 bytes) + ciphertext
                f.write(nonce)
                f.write(tag)
                f.write(ciphertext)
                
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Encryption failed: {str(e)}")
            
    def decrypt_file(self, file_path, output_path=None, password=None, temp=False):
        """
        Decrypt a file using AES-256-GCM
        
        Args:
            file_path: Path to the encrypted file
            output_path: Path where to save the decrypted file (default: original filename without .enc)
            password: Optional password to use (default: master password)
            temp: If True, create a temporary file for decryption
            
        Returns:
            Path to the decrypted file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # If no output path specified and not temp, use the original path without .enc extension
        if output_path is None and not temp:
            if file_path.endswith('.enc'):
                output_path = file_path[:-4]  # Remove .enc extension
            else:
                output_path = file_path + '.dec'
                
        # If temp is True, create a temporary file
        if temp:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, os.path.basename(file_path))
            if output_path.endswith('.enc'):
                output_path = output_path[:-4]
                
        try:
            # Derive the decryption key
            key = self.derive_key(password)
            
            # Read the encrypted file
            with open(file_path, 'rb') as f:
                nonce = f.read(16)
                tag = f.read(16)
                ciphertext = f.read()
                
            # Create cipher
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            
            # Decrypt the data
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            
            # Write the decrypted file
            with open(output_path, 'wb') as f:
                f.write(plaintext)
                
            # If temp, store the mapping for cleanup later
            if temp:
                self.temp_files[output_path] = file_path
                
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Decryption failed: {str(e)}")
            
    def cleanup_temp_file(self, temp_path):
        """
        Re-encrypt and remove a temporary decrypted file
        
        Args:
            temp_path: Path to the temporary decrypted file
        """
        if temp_path in self.temp_files:
            original_encrypted_path = self.temp_files[temp_path]
            
            try:
                # Re-encrypt the file if it still exists
                if os.path.exists(temp_path):
                    self.encrypt_file(temp_path, original_encrypted_path)
                    
                # Delete the temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
                # Remove from tracking dict
                del self.temp_files[temp_path]
                
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")
                
    def cleanup_all_temp_files(self):
        """Clean up all temporary decrypted files"""
        temp_paths = list(self.temp_files.keys())
        for temp_path in temp_paths:
            self.cleanup_temp_file(temp_path)
            
    def is_file_encrypted(self, file_path):
        """Check if a file is encrypted (has .enc extension or is in encrypted format)"""
        if file_path.endswith('.enc'):
            return True
            
        # Try to check file format
        try:
            with open(file_path, 'rb') as f:
                # Read the first 32 bytes (nonce + tag)
                header = f.read(32)
                # If file is smaller than 32 bytes, it's not in our encrypted format
                if len(header) < 32:
                    return False
                    
                # Try to decrypt with the key
                # This is a simple heuristic and might give false positives
                return True
                
        except Exception:
            return False
            
    def encrypt_directory(self, directory_path, password=None, recursive=True):
        """
        Encrypt all files in a directory
        
        Args:
            directory_path: Path to the directory
            password: Optional password to use (default: master password)
            recursive: If True, process subdirectories recursively
        """
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Not a directory: {directory_path}")
            
        encrypted_files = []
        failed_files = []
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                # Skip already encrypted files
                if file.endswith('.enc'):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    encrypted_path = self.encrypt_file(file_path, password=password)
                    # Remove the original file after encryption
                    os.remove(file_path)
                    encrypted_files.append(encrypted_path)
                except Exception as e:
                    failed_files.append((file_path, str(e)))
                    
            # If not recursive, break after processing the top directory
            if not recursive:
                break
                
        return {
            'encrypted': encrypted_files,
            'failed': failed_files
        }
        
    def decrypt_directory(self, directory_path, password=None, recursive=True):
        """
        Decrypt all encrypted files in a directory
        
        Args:
            directory_path: Path to the directory
            password: Optional password to use (default: master password)
            recursive: If True, process subdirectories recursively
        """
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Not a directory: {directory_path}")
            
        decrypted_files = []
        failed_files = []
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                # Only process encrypted files
                if not file.endswith('.enc'):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    decrypted_path = self.decrypt_file(file_path, password=password)
                    # Remove the encrypted file after decryption
                    os.remove(file_path)
                    decrypted_files.append(decrypted_path)
                except Exception as e:
                    failed_files.append((file_path, str(e)))
                    
            # If not recursive, break after processing the top directory
            if not recursive:
                break
                
        return {
            'decrypted': decrypted_files,
            'failed': failed_files
        }
