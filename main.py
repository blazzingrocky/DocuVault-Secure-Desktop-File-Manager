import os
from file_auto import FileAutomationSystem

if __name__ == "__main__":
    
    root_directory = os.getcwd()
    file_system = FileAutomationSystem(root_directory)
    file_system.create_extension_folders()
    file_system.create_subfolders()

    # Test moving a file to its extension folder and subfolder
    file_path = "paper.txt"
    file_system.move_to_subfolder(file_path)

    # Test metadata extraction
    # metadata = file_system.extract_metadata(file_path)
    # print(metadata)

    # # Test smart search
    # query = "example"
    # results = file_system.smart_search(query)
    # print(results)