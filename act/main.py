
from login import LoginPage
from database import create_database

# --- Main Execution ---

if __name__ == "__main__":
    create_database()  # Ensure database is created before running the app
    login_app = LoginPage()  # Start with the login page
    login_app.mainloop()  # Run the login application loop
