# Spotify Token Management — Auto-Refresh Guide

## Overview

The Madrid Dark Events Bot now uses **Refresh Tokens** for permanent, hands-free authentication. No manual token renewal needed after initial setup!

---

## Token Types

| Token | Lifespan | Purpose | Auto-Refresh? |
|-------|----------|---------|---------------|
| **Access Token** | 1 hour | Authenticate API requests | ❌ Manual |
| **Refresh Token** | Indefinite* | Generate new access tokens | ✅ Automatic |

*Refresh tokens don't technically expire unless user revokes them on Spotify.

---

## Initial Setup (One-Time)

### Step 1: Get Spotify Developer Credentials

1. Go to https://developer.spotify.com/dashboard
2. Create a new app
3. Copy your **Client ID** and **Client Secret**

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
```

### Step 2: Run Auth Script (Locally)

Execute this **on your personal machine** (not on the server):

```bash
python3 spotify_auth.py
```

This will:
1. Open your browser → Spotify login
2. Authorize the app
3. **Print your REFRESH TOKEN** (save this!)

### Step 3: Store Refresh Token

You'll receive output like:

```
YOUR REFRESH TOKEN (PERMANENT):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AQBXxxxxxYYYYYzzzzzz...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Save this safely.** This is your permanent authentication credential.

---

## How It Works

### Token Manager Flow

```
┌──────────────────────────────────────────────────────┐
│ Bot starts (Thursday 2 AM)                            │
└──────────────────────────────────────────────────────┘
  ↓
┌──────────────────────────────────────────────────────┐
│ SpotifyTokenManager.get_valid_access_token()         │
└──────────────────────────────────────────────────────┘
  ↓
  ├─ Is access token still valid? (expires_at > now)
  │  ├─ YES → Use it
  │  └─ NO → Proceed to refresh
  │
  ├─ Is refresh token available?
  │  ├─ YES → Use it to get new access token
  │  │         (POST to Spotify /api/token)
  │  │         ✅ Automatic renewal!
  │  │
  │  └─ NO → Use provided access token
  │          ⚠️  Will expire after 1 hour
  │
  ↓
┌──────────────────────────────────────────────────────┐
│ Return valid access token to bot                     │
└──────────────────────────────────────────────────────┘
  ↓
┌──────────────────────────────────────────────────────┐
│ Bot continues normally                               │
└──────────────────────────────────────────────────────┘
```

### Code Example

```python
from madrid_events_bot import SpotifyTokenManager, MadridEventsBot

# Initialize token manager (auto-renews if needed)
token_manager = SpotifyTokenManager(
    refresh_token="AQBXxxx...",  # Permanent
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
)

# Get valid token (auto-refreshes if expired)
access_token = token_manager.get_valid_access_token()

# Bot initializes with token manager
bot = MadridEventsBot(token_manager)
report = bot.run()
```

---

## Running the Bot

### With Refresh Token (Recommended ✅)

```bash
export SPOTIFY_REFRESH_TOKEN="AQBXxxx..."
export SPOTIFY_CLIENT_ID="your_id"
export SPOTIFY_CLIENT_SECRET="your_secret"

python3 madrid_events_bot.py
```

Or pass as argument:

```bash
python3 madrid_events_bot.py AQBXxxx...
```

**Result:** Token auto-refreshes every Thursday at 2 AM indefinitely ✅

### With Access Token (Fallback ⚠️)

```bash
export SPOTIFY_ACCESS_TOKEN="AQDST3uf..."
python3 madrid_events_bot.py
```

**⚠️ Warning:** Token expires after 1 hour. Use only for testing.

---

## Testing Token Manager

Run the test suite to verify auto-refresh:

```bash
python3 test_bot.py AQBXxxx...
```

Output will show:

```
PHASE 3: Testing Spotify Authentication (with Token Manager)
✅ Token Manager: Ready with refresh token
✅ Authenticated as: YOUR_USERNAME
```

---

## Troubleshooting

### "Token Expired"

**If you see:** `INVALID_SPOTIFY_TOKEN`

**Solution:** Check that refresh token is valid:
```bash
python3 spotify_auth.py  # Run locally again to get new refresh token
```

### "Token Not Working After 1 Hour"

**Cause:** Using access token without refresh token

**Solution:** Use refresh token instead:
```bash
export SPOTIFY_REFRESH_TOKEN="AQBXxxx..."
python3 madrid_events_bot.py
```

### "SpotifyTokenManager Error"

**Check environment variables:**
```bash
echo $SPOTIFY_CLIENT_ID
echo $SPOTIFY_CLIENT_SECRET
echo $SPOTIFY_REFRESH_TOKEN
```

All three should be set.

---

## Token Lifecycle

```
Day 1:
  ├─ User runs spotify_auth.py (locally)
  ├─ Gets refresh token (AQBXxxx...)
  └─ Stores it safely

Day 1 onwards:
  ├─ Bot runs weekly (Thursday 2 AM)
  ├─ TokenManager checks: Is access token valid?
  │  ├─ YES (within 1 hour) → Use current token
  │  └─ NO (expired) → Refresh via refresh token
  ├─ TokenManager requests new access token from Spotify
  ├─ Spotify validates refresh token ✅
  ├─ Returns new access token (valid for 1 hour)
  └─ Bot uses it

Year 1:
  ├─ Same cycle repeats every Thursday
  └─ No manual intervention needed ✅

Never (unless Spotify revokes):
  └─ Refresh token expires
```

---

## Security Notes

⚠️ **Never share your tokens:**
- Refresh token = permanent access to your Spotify data
- Treat like a password
- Don't commit to git or paste in messages

**Keep safe in:**
- Environment variables (never in .env files checked to git)
- Secure password manager
- Private notes

**If compromised:**
1. Go to https://www.spotify.com/account/apps
2. Revoke the application
3. Create new refresh token

---

## Advanced: Manual Token Rotation

If you want to rotate tokens for security:

```bash
# Get new refresh token
python3 spotify_auth.py

# Update environment variable
export SPOTIFY_REFRESH_TOKEN="new_AQBXxxx..."

# Next bot run will use new token automatically
```

---

## FAQ

**Q: Do I have to renew the refresh token?**
A: No. Refresh tokens don't expire unless Spotify revokes them or you manually revoke the app.

**Q: What if the bot can't reach Spotify during token refresh?**
A: It will use cached tokens if available, or fail gracefully with an error. Next week's run will try again.

**Q: Can I share the refresh token?**
A: Don't. It's equivalent to sharing your Spotify password.

**Q: Does the bot work without a refresh token?**
A: Yes, but only for 1 hour (using access token). After that, manual intervention needed.

---

## See Also

- `WORKFLOW.md` — Complete bot execution workflow
- `README.md` — Bot setup and usage
- `test_bot.py` — Run tests with token verification
