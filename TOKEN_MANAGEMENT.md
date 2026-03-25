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

### Simplified Token Manager Flow

**Strategy:** Refresh ONCE at startup, use for entire execution.

```
Thursday 2:00 AM
        ↓
┌──────────────────────────────────────────────────────┐
│ Bot starts                                            │
└──────────────────────────────────────────────────────┘
  ↓
┌──────────────────────────────────────────────────────┐
│ SpotifyTokenManager.__init__()                       │
│ (Refresh token → new access token, ONE TIME)         │
└──────────────────────────────────────────────────────┘
  ↓
  POST https://accounts.spotify.com/api/token
    ├─ grant_type: "refresh_token"
    ├─ refresh_token: "AQBXxxx..."
    ├─ client_id: "515debd..."
    └─ client_secret: "76aced..."
  ↓
  Spotify returns:
    └─ access_token: "AQDST3uf..." (valid for 1 hour)
  ↓
┌──────────────────────────────────────────────────────┐
│ token_manager.get_access_token()                     │
│ → Returns token for rest of execution                │
└──────────────────────────────────────────────────────┘
  ↓
┌──────────────────────────────────────────────────────┐
│ MadridEventsBot(token_manager)                       │
│ - Fetch Spotify data
│ - Scrape events
│ - Generate report
│ - Send to Telegram
└──────────────────────────────────────────────────────┘
  ↓
Thursday 2:30 AM
  └─ Bot complete, no more token operations
```

**Benefits:**
- ✅ Only 1 API call to Spotify per week (refresh)
- ✅ Minimal network traffic
- ✅ No polling or repeated checks
- ✅ Simple, efficient code

### Code Example

```python
from madrid_events_bot import SpotifyTokenManager, MadridEventsBot

# Initialize token manager
# Automatically refreshes at init using refresh token
token_manager = SpotifyTokenManager(
    refresh_token="AQBXxxx..."  # Permanent token
)
# Internal call:
#   POST /api/token with refresh_token
#   → Gets new access token (valid 1 hour)

# Bot initializes with refreshed token
bot = MadridEventsBot(token_manager)

# Entire execution uses the same access token
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
Day 1 (Setup):
  ├─ User runs: python3 spotify_auth.py (locally)
  ├─ Gets: Refresh Token "AQBXxxx..." (permanent)
  └─ Stores: Securely (env var, password manager, etc.)

Day 1 onwards (Automatic execution):
  ├─ Every Thursday 2:00 AM:
  │  ├─ Bot starts
  │  ├─ TokenManager refreshes at __init__():
  │  │  ├─ POST /api/token with refresh_token
  │  │  ├─ Spotify validates refresh token ✅
  │  │  ├─ Returns new access_token
  │  │  └─ Valid for 1 hour
  │  │
  │  ├─ Bot uses access_token for execution:
  │  │  ├─ Fetch user's top artists
  │  │  ├─ Scrape events
  │  │  └─ Send report
  │  │
  │  └─ Execution complete by 2:30 AM
  │     (access token still has 59+ minutes left)
  │
  └─ Next Thursday: Repeat

Week 1-52:
  ├─ Every Thursday: 1 refresh, 1 hour of API access
  ├─ Total: 52 refreshes/year, zero manual intervention
  └─ Network cost: Minimal (1 POST request/week)

Forever (unless revoked):
  └─ Refresh token never expires automatically ✅
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
