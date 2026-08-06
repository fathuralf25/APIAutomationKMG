from dotenv import load_dotenv
import os

# Load file .env
load_dotenv()

# API
BASE_URL = os.getenv("BASE_URL")

# Database
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
API_TOKEN = os.getenv("API_TOKEN") # Fallback if manual token is used
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TESTING_DOCS_URL = os.getenv("TESTING_DOCS_URL")