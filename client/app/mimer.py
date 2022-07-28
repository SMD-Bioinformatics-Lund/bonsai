"""Handlers for api services."""
import requests
from requests.structures import CaseInsensitiveDict
from pathlib import Path
from flask import current_app

def get_current_user(token):
    """Get current user from token"""
    # configure header
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    headers["Authorization"] = "Bearer {token}"

    # conduct query
    url = Path(current_app.config["MIMER_API_URL"], 'users', 'me')
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json

def get_auth_token(username: str, password: str) -> str:
    """Get authentication token from api"""
    url = Path(current_app.config["MIMER_API_URL"], 'token')
    resp = requests.post(url, data={username: username, password: password})
    # controll that request 
    resp.raise_for_status()
    return resp.json