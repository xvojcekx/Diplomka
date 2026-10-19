import sys
import os

# Ensure the 'app' directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

# Set testing environment variable
os.environ["TESTING"] = "1"

# Initialize test database
from database import init_db
init_db()
