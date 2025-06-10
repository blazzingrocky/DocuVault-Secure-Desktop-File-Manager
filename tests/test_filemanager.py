import unittest
import os
import shutil
import tempfile
import subprocess
from unittest.mock import patch, MagicMock
from io import StringIO
import sqlite3

# Import the FileManager class from filemanager.py
from filemanager import FileManager

class TestFileManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test method."""
        # Create temporary directories for testing
        self.test_dir = tempfile.mkdtemp()
        print(f"Created test directory: {self.test_dir}")
        print(f"Directory exists: {os.path.exists(self.test_dir)}")
        self.bin_dir = tempfile.mkdtemp()
        self.archive_dir = tempfile.mkdtemp()
        
        # Create a test database connection
        test_db_path = os.path.join(self.test_dir, 'test_filemanager.db')
        
        # Create a FileManager instance with test database
        self.file_manager = FileManager("test_user", self.bin_dir, self.archive_dir)
        
        # Override the database connection for testing
        self.file_manager.db_connection = sqlite3.connect(test_db_path, isolation_level=None)
        
        # Create test files and folders
        self.test_file = os.path.join(self.test_dir, "test_file.txt")
        with open(self.test_file, "w") as f:
            f.write("Test content")
        
        self.test_folder = os.path.join(self.test_dir, "test_folder")
        os.makedirs(self.test_folder, exist_ok=True)
    
    def tearDown(self):
        """Clean up after each test method."""
        # Remove temporary directories
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(self.bin_dir, ignore_errors=True)
        shutil.rmtree(self.archive_dir, ignore_errors=True)
        # shutil.os.remove('test_filemanager.db')
    
    def test_create_file(self):
        """Test creating a new file."""
        new_file = os.path.join(self.test_dir, "new_file.txt")
        print(f"Attempting to create file at: {new_file}")
        print(f"Directory exists: {os.path.exists(self.test_dir)}")
        print(f"File already exists: {os.path.exists(new_file)}")
        
        success, path = self.file_manager.create_file(self.test_dir, "new_file.txt")
        
        print(f"Success: {success}, Path: {path}")
        
        self.assertTrue(success)
        self.assertEqual(path, new_file)
        self.assertTrue(os.path.exists(new_file))
    
    def test_create_file_invalid_name(self):
        """Test creating a file with invalid name."""
        success, message = self.file_manager.create_file(self.test_dir, "")
        
        self.assertFalse(success)
        self.assertEqual(message, "No filename provided")
    
    def test_create_file_already_exists(self):
        """Test creating a file that already exists."""
        # Mock the messagebox.askyesno to return False (don't overwrite)
        with patch('tkinter.messagebox.askyesno', return_value=False):
            success, path = self.file_manager.create_file(self.test_dir, "test_file.txt")
            
            self.assertTrue(success)
            self.assertEqual(path, self.test_file)
    
    def test_create_folder(self):
        """Test creating a new folder."""
        new_folder = os.path.join(self.test_dir, "new_folder")
        success, path = self.file_manager.create_folder(self.test_dir, "new_folder")
        
        self.assertTrue(success)
        self.assertEqual(path, new_folder)
        self.assertTrue(os.path.isdir(new_folder))
    
    def test_create_folder_invalid_name(self):
        """Test creating a folder with invalid name."""
        success, message = self.file_manager.create_folder(self.test_dir, "")
        
        self.assertFalse(success)
        self.assertEqual(message, "No folder name provided")
    
    def test_delete_item_to_bin(self):
        """Test moving an item to bin."""
        items = [self.test_file]
        
        # Mock allow_access and restrict_access functions
        with patch('filemanager.allow_access'), patch('filemanager.restrict_access'):
            result = self.file_manager.delete_item(self.test_dir, items, permanently=False)
            
            self.assertEqual(result["success_count"], 1)
            self.assertFalse(os.path.exists(self.test_file))
            # Check if file is in bin
            self.assertTrue(any(os.path.basename(self.test_file) in f for f in os.listdir(self.bin_dir)))
    
    def test_delete_item_permanently(self):
        """Test deleting an item permanently."""
        items = [self.test_file]
        
        result = self.file_manager.delete_item(self.test_dir, items, permanently=True)
        
        self.assertEqual(result["success_count"], 1)
        self.assertFalse(os.path.exists(self.test_file))
        # Check that file is not in bin
        self.assertFalse(any(os.path.basename(self.test_file) in f for f in os.listdir(self.bin_dir)))
    
    def test_move_item(self):
        """Test moving an item to another location."""
        dest_dir = os.path.join(self.test_dir, "destination")
        os.makedirs(dest_dir, exist_ok=True)
        print(f"Destination directory: {dest_dir}")
        items = [self.test_file]
        result = self.file_manager.move_item(items, dest_dir)
        # print(result["success_count"])
        print("Success count:", result["success_count"])
        print("Destination path:", dest_dir)
        print("File in new Destination:", os.path.exists(os.path.join(dest_dir, os.path.basename(self.test_file))))
        self.assertEqual(result["success_count"], 1)
        self.assertFalse(os.path.exists(self.test_file))
        self.assertTrue(os.path.exists(os.path.join(dest_dir, os.path.basename(self.test_file))))
    
    def test_move_item_conflict(self):
        """Test moving an item when destination already has file with same name."""
        dest_dir = os.path.join(self.test_dir, "destination")
        os.makedirs(dest_dir, exist_ok=True)
        
        # Create a file with the same name in destination
        dest_file = os.path.join(dest_dir, os.path.basename(self.test_file))
        with open(dest_file, "w") as f:
            f.write("Destination content")
        
        # Mock messagebox.askyesno to return True (overwrite)
        with patch('tkinter.messagebox.askyesno', return_value=True):
            items = [self.test_file]
            result = self.file_manager.move_item(items, dest_dir)
            
            self.assertEqual(result["success_count"], 1)
            self.assertFalse(os.path.exists(self.test_file))
            self.assertTrue(os.path.exists(dest_file))
            
            # Verify content was overwritten
            with open(dest_file, "r") as f:
                self.assertEqual(f.read(), "Test content")
    
    def test_copy_item(self):
        """Test copying an item to another location."""
        dest_dir = os.path.join(self.test_dir, "destination")
        os.makedirs(dest_dir, exist_ok=True)
        
        items = [self.test_file]
        result = self.file_manager.copy_item(items, dest_dir)
        
        self.assertEqual(result["success_count"], 1)
        self.assertTrue(os.path.exists(self.test_file))  # Original still exists
        self.assertTrue(os.path.exists(os.path.join(dest_dir, os.path.basename(self.test_file))))
    
    def test_rename_item(self):
        """Test renaming an item."""
        new_name = "renamed_file.txt"
        new_path = os.path.join(self.test_dir, new_name)
        print(f"Old path: {self.test_file}, New path: {new_path}")
        
        # Mock the database connection and cursor
        with patch.object(self.file_manager, 'db_connection') as mock_conn:
            mock_cursor = mock_conn.cursor.return_value
            
            success, path = self.file_manager.rename_item(self.test_file, new_name)
            print(f"Success: {success}, Path: {path}")
            
            self.assertTrue(success)
            self.assertEqual(path, new_path)
            self.assertFalse(os.path.exists(self.test_file))
            self.assertTrue(os.path.exists(new_path))

    
    def test_rename_item_conflict(self):
        """Test renaming when target name already exists."""
        # Create a file with the target name
        conflict_file = os.path.join(self.test_dir, "conflict.txt")
        with open(conflict_file, "w") as f:
            f.write("Conflict content")
        
        # Mock messagebox.askyesno to return False (don't overwrite)
        with patch('tkinter.messagebox.askyesno', return_value=False):
            success, path = self.file_manager.rename_item(self.test_file, "conflict.txt")
            
            self.assertTrue(success)
            self.assertEqual(path, self.test_file)  # Should return original path
            self.assertTrue(os.path.exists(self.test_file))
            self.assertTrue(os.path.exists(conflict_file))
    
    def test_empty_bin(self):
        """Test emptying the bin directory."""
        # Add a file to the bin
        bin_file = os.path.join(self.bin_dir, "bin_file.txt")
        with open(bin_file, "w") as f:
            f.write("Bin content")
        
        result = self.file_manager.empty_bin()
        
        self.assertEqual(result["success_count"], 1)
        self.assertFalse(os.path.exists(bin_file))
    
    def test_restore_item(self):
        """Test restoring an item from bin."""
        # Add a file to the bin
        bin_file = os.path.join(self.bin_dir, "bin_file.txt")
        with open(bin_file, "w") as f:
            f.write("Bin content")
        
        items = [bin_file]
        result = self.file_manager.restore_item(items, self.test_dir)
        
        self.assertEqual(result["success_count"], 1)
        self.assertFalse(os.path.exists(bin_file))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "bin_file.txt")))
    
    def test_open_file(self):
        """Test opening a file."""
        def side_effect(*args, **kwargs):
            # Print arguments for debugging
            print(f"Popen called with: {args}, {kwargs}")
            mock = MagicMock()
            mock.communicate.return_value = (b'output', b'error')
            mock.returncode = 0
            return mock
            
        with patch('filemanager.subprocess.Popen', side_effect=side_effect) as mock_popen:
            success, message = self.file_manager.open_file(self.test_file)
            
            self.assertTrue(success)
            mock_popen.assert_called()
            self.assertEqual(message, "File opened successfully")
    def test_open_file(self):
        """Test opening a file."""
        # Patch the correct import path
        with patch('filemanager.subprocess.Popen') as mock_popen:
            print(f"Mocked subprocess.Popen: {mock_popen}")
            success, message = self.file_manager.open_file(self.test_file)
            # print(f"Success: {success}, Message: {message}")
            self.assertTrue(success)
            self.assertEqual(message, "File opened successfully")
            # mock_popen.assert_called()

    
    def test_recursive_search(self):
        """Test searching for files recursively."""
        # Create some files for searching
        os.makedirs(os.path.join(self.test_dir, "subdir"), exist_ok=True)
        with open(os.path.join(self.test_dir, "findme.txt"), "w") as f:
            f.write("Find this file")
        with open(os.path.join(self.test_dir, "subdir", "findme_too.txt"), "w") as f:
            f.write("Find this file too")
        
        results, found = self.file_manager.recursive_search(self.test_dir, "findme")
        
        self.assertTrue(found)
        self.assertEqual(len(results), 2)  # Should find both files

if __name__ == '__main__':
    unittest.main()
    
#     # Run the tests
