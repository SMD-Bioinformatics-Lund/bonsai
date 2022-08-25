"""Configuration of web site"""
import os

# Setup api url
MIMER_API_URL = os.getenv("MIMER_API_URL", "http://api:8000")

# Session secret key
SECRET_KEY = b"not-so-secret"