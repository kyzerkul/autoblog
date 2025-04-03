from flask import Flask, request
import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from app.py
try:
    from app import app as flask_app
except ImportError as e:
    print(f"Error importing app: {str(e)}")
    flask_app = Flask(__name__)
    
    @flask_app.route('/')
    def error_index():
        return "Import error occurred: " + str(e)

# Export Flask application for Vercel
app = flask_app
