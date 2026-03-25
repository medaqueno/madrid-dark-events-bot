#!/usr/bin/env python3
"""
Spotify OAuth Authentication Script
Run this locally to obtain refresh token for the Madrid Dark Events Bot.

Usage:
    python3 spotify_auth.py

This will:
1. Open a browser to Spotify login
2. Save your refresh token (long-lived) to .spotify_cache
3. Print credentials for bot to use

The REFRESH TOKEN is permanent and will auto-renew access tokens.

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
    refresh_token = token_info.get('refresh_token', 'N/A')
    expires_in = token_info.get('expires_in', 3600)

    print("✅ Authentication successful!")
    print()
    print("=" * 70)
    print("🎵 SPOTIFY CREDENTIALS FOR MADRID DARK EVENTS BOT")
    print("=" * 70)
    print()

    print("📝 YOUR REFRESH TOKEN (PERMANENT):")
    print("-" * 70)
    print(refresh_token)
    print("-" * 70)
    print()
    print("⚠️  SAVE THIS REFRESH TOKEN SECURELY!")
    print("   This token lasts indefinitely and allows the bot to auto-renew.")
    print()

    print("📝 CURRENT ACCESS TOKEN (expires in ~1 hour):")
    print("-" * 70)
    print(access_token)
    print("-" * 70)
    print()

    print("📌 SETUP INSTRUCTIONS:")
    print()
    print("1. Save the REFRESH TOKEN above in a safe location")
    print()
    print("2. Provide the bot with ONE of these options:")
    print("   a) The REFRESH TOKEN (recommended - auto-renews forever)")
    print("   b) The ACCESS TOKEN (expires in 1 hour - not recommended)")
    print()
    print("3. The bot will:")
    print("   - Use refresh token to auto-renew access tokens weekly")
    print("   - Never require manual intervention")
    print("   - Work indefinitely")
    print()

    print("💾 Tokens cached in: .spotify_cache (SpotifyOAuth)")
    print()

    # Save refresh token to a separate file for easy access
    refresh_token_file = Path(".spotify_refresh_token")
    refresh_token_file.write_text(refresh_token)
    print(f"✅ Refresh token also saved to: {refresh_token_file}")
    print()

if __name__ == "__main__":
    main()
