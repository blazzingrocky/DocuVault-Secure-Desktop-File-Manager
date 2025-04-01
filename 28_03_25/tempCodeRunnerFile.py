    def test_create_file_already_exists(self):
        """Test creating a file that already exists."""
        # Mock the messagebox.askyesno to return False (don't overwrite)
        with patch('tkinter.messagebox.askyesno', return_value=False):
            success, path = self.file_manager.create_file(self.test_dir, "test_file.txt")
            
            self.assertTrue(success)
            self.assertEqual(path, self.test_file)