import google.generativeai as genai
from fastapi import FastAPI, Body

class GeminiAPIService:
   '''
   A service to interact with Google's Gemini API through FastAPI.
   Provides endpoints for generating content based on text prompts.
   '''
    
   def __init__(self, api_key):
      # Configure the API with your key
      genai.configure(api_key=api_key)

      self.docu = '''
      DocuVault: Secure Desktop File Management System

      Features:
      1. Authentication: Secure login system with username/password authentication and session management.
         - Uses bcrypt for password hashing in login.py
         - Supports user registration with custom automation folder setup
         - Includes inactivity timeout (30 minutes) for security

      2. File Management: Complete file operations with modern UI.
         - Create, rename, move, copy, and delete files/folders
         - Sort files by name, date, or size
         - Advanced search with filters (file type, date, size)
         - Context menus for quick operations
         - File metadata viewing

      3. Automation: AI-powered file classification system.
         - Automatically categorizes files based on content
         - Supports text files (.txt) and images (.jpg, .png)
         - Creates organized folder structure
         - Uses machine learning for content analysis
         - Accessible via the Automation Window

      4. Cloud Integration: Nextcloud connectivity for remote storage.
         - Upload/download files to Nextcloud
         - Search cloud storage
         - Secure credential storage with encryption
         - Progress tracking for cloud operations

      5. Database: SQLite backend for user data and logs.
         - Stores user credentials and settings
         - Tracks user activity with detailed logs
         - Supports account management (creation/deletion)
         - Maintains cloud connection information

      6. Utilities: Helper functions for enhanced usability.
         - Custom file/directory selection dialogs
         - Path comparison and validation
         - Tooltips for UI elements
         - Progress indicators for operations

      7. Recycle Bin: Safe file deletion with recovery options.
         - Move to bin instead of permanent deletion
         - Restore files from bin
         - Empty bin functionality

      Key Files:
      - main.py: Application entry point
      - login.py: Authentication system
      - filemanager.py: Main file management interface
      - automation.py: AI-powered file organization
      - database.py: Data persistence layer
      - cloud.py: Nextcloud integration
      - utility.py: Helper functions and UI components
      '''
        
      # Initialize the model
      self.model = genai.GenerativeModel(
         model_name='gemini-1.5-flash',
         system_instruction="You are a helpful assistant for helping user, using the product : f{self.docu}."
      )
      
      # Create FastAPI instance
      self.app = FastAPI(title="Gemini API Service")
      
      # Setup routes
      self.setup_routes()
   
   def setup_routes(self):
      @self.app.post("/chat")
      async def chat(messages: list = Body(...)):
         return await self.process_chat(messages)
   
   async def process_chat(self, messages: list):
      chat = self.model.start_chat(history=messages)
      last_message = messages[-1]["content"]
      response = chat.send_message(last_message)
      return {"response": response.text}
   
   async def process_chat(self, messages: list):
      # Convert OpenAI-style messages to Gemini format
      gemini_messages = []
      for message in messages:
         role = message["role"]
         content = message["content"]
        
         # Map OpenAI roles to Gemini roles
         if role == "user":
            gemini_role = "user"
         elif role == "assistant":
            gemini_role = "model"
         else:
            gemini_role = "user"  # Default fallback
        
         # Create properly formatted Gemini message
         gemini_message = {
            "role": gemini_role,
            "parts": [{"text": content}]
         }
         gemini_messages.append(gemini_message)
    
      # Start chat with properly formatted history
      chat = self.model.start_chat(history=gemini_messages)
    
      # Get the last user message
      last_message = messages[-1]["content"]
    
      # Send the message and get response
      response = chat.send_message(last_message)
    
      return {"response": response.text}

   
   def serve_model(self, host="0.0.0.0", port=8000):
      import uvicorn
      uvicorn.run(self.app, host=host, port=port)