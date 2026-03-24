# Madrid Dark Events Bot 🎸

Weekly discovery of dark/gothic/metal events in Madrid based on your Spotify listening preferences.

**Runs:** Thursday 2:00 AM
**Reports:** Telegram group
**Status:** Active in NanoClaw cluster

---

## Setup (One-time)

### 1. Get Spotify Credentials

You need a Spotify Developer account:

1. Go to https://developer.spotify.com/dashboard
2. Create an app
3. Get your `Client ID` and `Client Secret`
4. Set these as environment variables:

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
```

### 2. Run OAuth Authentication (Locally)

Run the auth script **on your local machine** (not on the server):

```bash
python3 spotify_auth.py
```

This will:
- Open your browser to Spotify login
- Ask you to authorize the app
- Print your access token

**Copy the token and give it to the bot.**

---

## How It Works

1. **Analyze Your Taste** — Uses your top Spotify artists/tracks to infer dark music preferences
2. **Scrape Sources** — Collects events from:
   - PlanetM (Madrid nightclub)
   - GotiFiestas.com (goth/dark parties)
   - es.concerts-metal.com (metal concerts)
   - MadnessLive.es (live music events)
3. **Filter & Rank** — Prioritizes events matching your dark genre taste
4. **Send Report** — Posts weekly digest to Telegram

---

## Dark Genres Supported

- Gothic / Gothic Rock
- Black Metal / Doom Metal / Death Metal
- Post-Metal / Post-Rock
- Shoegaze
- Neofolk / Darkwave
- Industrial / Coldwave
- Dark Electronic

---

## Usage

### Run Manually

```bash
python3 madrid_events_bot.py <spotify_access_token>
```

Or with environment variable:

```bash
export SPOTIFY_ACCESS_TOKEN="your_token"
python3 madrid_events_bot.py
```

### Running in NanoClaw

The bot runs automatically every Thursday at 2:00 AM and posts results to Telegram.

To manually trigger:
```bash
/madrid-events  # In Telegram group
```

---

## Customization

### Add New Event Sources

Edit `madrid_events_bot.py` and add a new scraper function:

```python
def scrape_newsource(self) -> List[Dict]:
    events = []
    try:
        # Your scraping code here
        pass
    except Exception as e:
        logger.warning(f"Error: {e}")
    return events
```

Then call it in `scrape_all_sources()`:
```python
all_events.extend(self.scrape_newsource())
```

### Adjust Genre Preferences

Modify `DARK_GENRES` dictionary to add/remove genres and their weight (0-1):

```python
DARK_GENRES = {
    'gothic': 0.9,
    'your_genre': 0.8,
    ...
}
```

---

## Architecture

```
spotify_auth.py          ← Run locally, get token
    ↓
madrid_events_bot.py     ← Main bot script
    ├─ get_user_dark_preferences()  → Spotify API
    ├─ scrape_planetm()             → Web scraping
    ├─ scrape_gotifiestas()         → Web scraping
    ├─ scrape_concerts_metal()      → Web scraping
    ├─ scrape_madnesslive()         → Web scraping
    └─ generate_report()            → Telegram format
        ↓
    mcp__nanoclaw__send_message()   → Telegram group
```

---

## Troubleshooting

### "Missing Spotify credentials"

```bash
export SPOTIFY_CLIENT_ID="your_id"
export SPOTIFY_CLIENT_SECRET="your_secret"
```

### Token expired

Spotify tokens expire after 1 hour. Run `spotify_auth.py` again.

### Empty event results

Some sources may be temporarily unavailable. Check logs:
```bash
tail -f /var/log/nanoclaw/madrid-events.log
```

### Want to add/remove sources?

Message the bot in Telegram:
```
/add-source <url>
/remove-source <name>
```

(Feature in development)

---

## Future Enhancements

- [ ] Auto-discover new event sources
- [ ] Filter by venue proximity
- [ ] Ticket price integration
- [ ] Multi-city support
- [ ] User preference learning

---

## License

MIT

---

## Contacts / Questions

Built for NanoClaw cluster • Madrid • 2026
