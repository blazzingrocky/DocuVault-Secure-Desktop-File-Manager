 # def move_item(self):
    #     selection = self.file_tree.selection()
    #     if selection:
    #         item_id = selection[0]
    #         item_values = self.file_tree.item(item_id, 'values')
    #         if item_values:
    #             item_type, item_path = item_values
    #             dest_dialog = CustomDirectoryDialog(self.parent, self.current_dir)
    #             self.parent.wait_window(dest_dialog)  # Wait for dialog to close
    #             if dest_dialog.selected_path:
    #                 dest = dest_dialog.selected_path
    #                 try:
    #                     shutil.move(item_path, dest)
    #                     self.update_file_list()
    #                 except Exception as e:
    #                     messagebox.showerror("Error", f"Could not move item: {e}")