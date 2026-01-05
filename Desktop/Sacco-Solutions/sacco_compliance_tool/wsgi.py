# PythonAnywhere WSGI Configuration File
# Save this as: /var/www/wsgi.py

import sys
import os

# Add your project to the Python path
project_home = '/home/yourusername/amana'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import your Flask app
from app import app as application

# Configure Flask for production
application.secret_key = os.environ.get('SECRET_KEY', 'vimbatech-secret-key-2024')

# Set production mode
application.config['ENV'] = 'production'
application.config['DEBUG'] = False
application.config['TESTING'] = False

# Set upload folder (PythonAnywhere specific)
application.config['UPLOAD_FOLDER'] = '/home/yourusername/amana/uploads'
application.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(application.config['UPLOAD_FOLDER'], exist_ok=True)
