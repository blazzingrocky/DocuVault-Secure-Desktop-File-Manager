# DocuVault: Secure Desktop File Manager
DocuVault is a comprehensive desktop file management solution built with Python and Tkinter that provides advanced file organization, security, and automation features for efficient document handling.
## Features
Core File Management
Basic Operations: Copy, move, delete, and rename files and folders with intuitive interface

Recycle Bin: Safely delete files with the ability to restore them later

Archive System: Automatically archive old files based on customizable age thresholds

Search Functionality: Powerful search with filters for file type, date, and size

Sort Options: Organize files by name, date, or size with a single click

## Security
User Authentication: Secure login system with username and password protection

File Encryption: Built-in AES-256-GCM encryption for sensitive files

Activity Logging: Comprehensive logging of all file operations for accountability

Auto-logout: Automatic session termination after period of inactivity

## Automation
AI-Powered Classification: Automatically categorize files based on content analysis

Scheduled Backups: Configure automatic backups of frequently accessed files

File Monitoring: Track file access patterns to optimize organization

Auto-archiving: Set custom thresholds for moving older files to archive

## Cloud Integration
Nextcloud Support: Connect to Nextcloud for remote file storage

Cloud Search: Search files stored in the cloud from within the application

Synchronization: Keep local and cloud files in sync

File Sharing: Share cloud-stored files directly from the interface

## User Interface
Modern Design: Clean, intuitive interface with light and dark themes

File Preview: Built-in preview for common file types

Dashboard: Visual overview of storage usage and file distribution

Context Menus: Right-click functionality for quick access to common operations

## Advanced Features
Multi-select Operations: Perform actions on multiple files simultaneously

Drag and Drop: Intuitive file movement between folders

Custom Filters: Save and apply custom search filters

Path Navigation: Breadcrumb-style navigation for easy directory traversal

Account Management: User profile settings and account deletion options

ChatBot: Provides user assistance

## Testing
Unittest module of Python have been used to test the backend functionalities.

## INSTALLATION GUIDLINE

### Prerequisites
Python 3.7 or higher

Tailscale

### Required Python packages (install via pip):

text
pip install tkinter pillow pycryptodome schedule requests

### Setup
Clone the repository:

text
git clone https://github.com/blazzingrocky/DocuVault-Secure-Desktop-File-Manager.git
cd docuvault

### Run the application:

text
python main.py
On first run, create a new account to get started.

### Usage
Getting Started
Login/Register: Create an account or log in with existing credentials

Navigation: Use the toolbar buttons to navigate between directories

File Operations: Right-click on files or use the toolbar for common operations

Dashboard: View file statistics and storage usage at a glance

### Automation Setup
1. Go to Settings → Automation

2. Configure the automation folder location

3. Enable AI classification for document and image sorting

4. Set up auto-archiving preferences for older files

### Encryption
1. Select files you want to encrypt

2. Click the "Encrypt Files" button

3. Click the "Decrypt Files" button

### Cloud Setup
1.Go to Settings → Cloud Setup

2.Enter your Nextcloud server URL and credentials

3. Use the cloud buttons to synchronize and manage remote files

Search cloud storage directly from the main interface

4. Make sure Tailscale is installed in your machine


## Project Structure
main.py: Application entry point

login.py: User authentication system

gui.py: Main file manager interface

newfilemanager.py: Core file operations implementation

newautomation.py: Automation and AI classification features

encryption.py: File encryption/decryption functionality

database.py: SQLite database management

cloud.py: Cloud storage integration

dashboard.py: Analytics and statistics visualization

utility.py: Helper functions and custom dialogs

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

Fork the repository

Create your feature branch (git checkout -b feature/amazing-feature)

Commit your changes (git commit -m 'Add some amazing feature')

Push to the branch (git push origin feature/amazing-feature)

Open a Pull Request

License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments
The Tkinter library for providing the GUI framework

PyCryptodome for encryption capabilities

The open-source community for various libraries and inspiration

Azure theme for the modern UI appearance

## Future Development
Mobile companion app for remote access

Additional cloud storage providers (Google Drive, Dropbox)

Enhanced AI capabilities for document analysis and tagging

Cross-platform compatibility improvements

Collaborative editing features

Version control for important documents

Extended file preview capabilities

Include tagging feature of files
