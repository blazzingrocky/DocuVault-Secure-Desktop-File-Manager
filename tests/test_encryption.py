import unittest
import os
import shutil
import tempfile
import subprocess
from unittest.mock import patch, MagicMock
from io import StringIO
import sqlite3
import unittest
from unittest.mock import Mock, patch, mock_open
import os
import tempfile
import shutil
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

# Import the FileEncryptor class (assuming it's in a module named encryption)
from encryption import FileEncryptor

class TestFileEncryption(unittest.TestCase):
    """Test cases for FileEncryptor encrypt_file and decrypt_file methods."""
    
    def setUp(self):
        """Set up test environment before each test method."""
        self.encryptor = FileEncryptor()
        self.encryptor.set_master_password("test_password")
        
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a test file with some content
        self.test_file_path = os.path.join(self.test_dir, "test_file.txt")
        with open(self.test_file_path, 'w') as f:
            f.write("This is test content for encryption and decryption tests.")
        
        # Path for the encrypted file
        self.encrypted_file_path = self.test_file_path + ".enc"
        
        # Path for decrypted file when testing temp decryption
        self.temp_decrypted_path = os.path.join(self.test_dir, "temp_decrypted.txt")
    
    def tearDown(self):
        """Clean up after each test method."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)
    
    def test_encrypt_file_success(self):
        """Test successful file encryption."""
        # Encrypt the test file
        result = self.encryptor.encrypt_file(self.test_file_path)
        
        # Check that encryption was successful
        self.assertTrue(result)
        
        # Check that the encrypted file exists
        self.assertTrue(os.path.exists(self.encrypted_file_path))
        
        # Check that the encrypted file is different from the original
        with open(self.test_file_path, 'rb') as original:
            original_content = original.read()
        
        with open(self.encrypted_file_path, 'rb') as encrypted:
            encrypted_content = encrypted.read()
        
        self.assertNotEqual(original_content, encrypted_content)
    
    def test_decrypt_file_success(self):
        """Test successful file decryption."""
        # First encrypt the file
        self.encryptor.encrypt_file(self.test_file_path)
        
        # Remove the original file to simulate normal behavior
        os.remove(self.test_file_path)
        
        # Decrypt the file
        result = self.encryptor.decrypt_file(self.encrypted_file_path)
        
        # Check that decryption was successful
        self.assertTrue(result)
        
        # Check that the decrypted file exists
        self.assertTrue(os.path.exists(self.test_file_path))
        
        # Check that the content matches the original
        with open(self.test_file_path, 'r') as f:
            decrypted_content = f.read()
        
        self.assertEqual(decrypted_content, "This is test content for encryption and decryption tests.")
    
    def test_temp_decrypt_file(self):
        """Test decryption to a temporary file without removing the encrypted file."""
        # First encrypt the file
        self.encryptor.encrypt_file(self.test_file_path)
        
        # Remove the original file
        os.remove(self.test_file_path)
        
        # Decrypt to a temporary file
        temp_file = self.encryptor.decrypt_file(self.encrypted_file_path, temp=True)
        
        # Check that temp decryption was successful
        self.assertIsNotNone(temp_file)
        self.assertTrue(os.path.exists(temp_file))
        
        # Check that the encrypted file still exists
        self.assertTrue(os.path.exists(self.encrypted_file_path))
        
        # Check content of temp file
        with open(temp_file, 'r') as f:
            temp_content = f.read()
        
        self.assertEqual(temp_content, "This is test content for encryption and decryption tests.")
        
        # Clean up the temp file
        os.remove(temp_file)
    
    @patch('encryption.FileEncryptor.set_master_password')
    def test_encrypt_without_password(self, mock_set_password):
        """Test encryption when master password is not set."""
        # Reset the encryptor to not have a password
        self.encryptor = FileEncryptor()
        
        # Mock the set_master_password to do nothing
        mock_set_password.return_value = None
        
        # Attempt to encrypt without a password should raise an exception
        with self.assertRaises(Exception):
            self.encryptor.encrypt_file(self.test_file_path)
    
    @patch('encryption.FileEncryptor.set_master_password')
    def test_decrypt_without_password(self, mock_set_password):
        """Test decryption when master password is not set."""
        # Create an encrypted file first with a password
        self.encryptor.encrypt_file(self.test_file_path)
        
        # Reset the encryptor to not have a password
        self.encryptor = FileEncryptor()
        
        # Mock the set_master_password to do nothing
        mock_set_password.return_value = None
        
        # Attempt to decrypt without a password should raise an exception
        with self.assertRaises(Exception):
            self.encryptor.decrypt_file(self.encrypted_file_path)
    
    def test_decrypt_with_wrong_password(self):
        """Test decryption with an incorrect password."""
        # Encrypt with the correct password
        self.encryptor.encrypt_file(self.test_file_path)
        
        # Create a new encryptor with a different password
        wrong_encryptor = FileEncryptor()
        wrong_encryptor.set_master_password("wrong_password")
        
        # Attempt to decrypt with the wrong password should fail
        with self.assertRaises(Exception):
            wrong_encryptor.decrypt_file(self.encrypted_file_path)
    
    def test_is_file_encrypted(self):
        """Test the is_file_encrypted method."""
        # Initially, the file is not encrypted
        self.assertFalse(self.encryptor.is_file_encrypted(self.test_file_path))
        
        # Encrypt the file
        self.encryptor.encrypt_file(self.test_file_path)
        
        # Now the encrypted file should be detected as encrypted
        self.assertTrue(self.encryptor.is_file_encrypted(self.encrypted_file_path))
    
    @patch('os.path.getsize')
    def test_encrypt_large_file(self, mock_getsize):
        """Test encryption of a large file."""
        # Mock the file size to be large (100MB)
        mock_getsize.return_value = 100 * 1024 * 1024
        
        # Encrypt the "large" file
        self.encryptor.encrypt_file(self.test_file_path)
        
        # Check that encryption was still successful
        self.assertTrue(os.path.exists(self.encrypted_file_path))
    


if __name__ == '__main__':
    unittest.main()
