#!/usr/bin/env python3
"""
Spotify OAuth Authentication Script
Run this locally to obtain an access token for the Madrid Dark Events Bot.

Usage:
    python3 spotify_auth.py

This will:
1. Open a browser to Spotify login
2. Save your access token to .spotify_cache file
3. Print the token for you to share with the bot

Requirements:
    - SPOTIFY_CLIENT_ID environment variable
    - SPOTIFY_CLIENT_SECRET environment variable
"""

import os
import sys
import json
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def main():
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("ERROR: Missing Spotify credentials!")
        print("Set these environment variables:")
        print("  export SPOTIFY_CLIENT_ID=your_client_id")
        print("  export SPOTIFY_CLIENT_SECRET=your_client_secret")
        sys.exit(1)

    # Configure OAuth with localhost redirect
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8888/callback",
        scope="user-library-read user-top-read",
        cache_path=".spotify_cache"
    )

    print("🎵 Spotify OAuth Authentication")
    print("=" * 50)
    print()
    print("Opening Spotify login in your browser...")
    print("This window will prompt you to authorize the app.")
    print()

    # Get token (will open browser if needed)
    token_info = sp_oauth.get_access_token()
    access_token = token_info['access_token']

    print("✅ Authentication successful!")
    print()
    print("📝 YOUR ACCESS TOKEN:")
    print("-" * 50)
    print(access_token)
    print("-" * 50)
    print()
    print("📌 NEXT STEPS:")
    print("1. Copy the token above")
    print("2. Share it with the Madrid Dark Events Bot")
    print("3. The bot will use it to infer your music preferences")
    print()
    print("💾 Token cached in: .spotify_cache")
    print("⏱️  Token expires in 1 hour. Refresh as needed.")
    print()

if __name__ == "__main__":
    main()
