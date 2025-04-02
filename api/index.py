from flask import Flask, jsonify, render_template, request, redirect, url_for
import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import necessary modules
from app import app as flask_app

# For Vercel serverless function
def handler(request, context):
    """Serverless function handler for Vercel"""
    return flask_app(request['headers'].get('Host', ''))

# For local development
if __name__ == "__main__":
    flask_app.run(debug=True)

# Export Flask application for Vercel
app = flask_app
