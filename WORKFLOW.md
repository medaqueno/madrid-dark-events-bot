# Madrid Dark Events Bot — Execution Workflow

## Overview

This document describes the complete execution workflow when the scheduled task runs every Thursday at 2:00 AM in the NanoClaw cluster.

---

## Timeline & Sequence

```
Thursday 2:00 AM (UTC)
        ↓
[1] Task Trigger
        ↓
[2] Environment Setup
        ↓
[3] Dependency Installation
        ↓
[4] Spotify Authentication
        ↓
[5] User Preference Analysis
        ↓
[6] Multi-Source Event Scraping
        ↓
[7] Event Filtering & Ranking
        ↓
[8] Report Generation
        ↓
[9] Telegram Delivery
        ↓
Thursday 2:15-2:30 AM: Complete
```

---

## Detailed Steps

### [1] Task Trigger
**Time:** Thursday 2:00 AM UTC
**Component:** NanoClaw scheduler (cron: `0 2 * * 4`)
**Action:** Wakes up Madrid Events Bot agent in isolated context
**Duration:** Instant

**Status Check:**
- ✅ Task activated
- ✅ All environment variables loaded (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, BRAVE_SEARCH_API_KEY)
- ✅ Isolated execution context initialized (no conversation history)

---

### [2] Environment Setup
**Time:** 2:00-2:01 AM
**Component:** Python bot initialization
**Action:** Load configuration and environment variables

```python
# Loaded from NanoClaw environment:
SPOTIFY_CLIENT_ID          = "from env"
SPOTIFY_CLIENT_SECRET      = "from env"
SPOTIFY_ACCESS_TOKEN       = "AQDST3ufeQobUAQ3OKOHI6H..." (hardcoded in task)
BRAVE_SEARCH_API_KEY       = "from env"

# Bot configuration:
DARK_GENRES = {
    'gothic': 0.9,
    'black metal': 1.0,
    'doom metal': 1.0,
    'post-metal': 1.0,
    ...
}

SOURCES = [
    'PlanetM',
    'GotiFiestas',
    'ConcertsMetal',
    'MadnessLive'
]
```

**Status Check:**
- ✅ All credentials valid
- ✅ Dark genres dictionary loaded
- ✅ Event sources configured

---

### [3] Dependency Installation
**Time:** 2:01-2:02 AM
**Component:** pip package manager
**Action:** Ensure all Python dependencies are available

```bash
pip3 install -q \
  spotipy==2.23.0 \
  requests==2.31.0 \
  beautifulsoup4==4.12.2 \
  lxml==4.9.3
```

**Outcome:**
- ✅ spotipy — Spotify API client
- ✅ requests — HTTP client for web scraping
- ✅ beautifulsoup4 — HTML parsing
- ✅ lxml — XML/HTML parser backend

**If dependencies fail:** Continue anyway (cached from previous runs)

---

### [4] Spotify Authentication
**Time:** 2:02-2:03 AM
**Component:** `MadridEventsBot.spotify` (spotipy client)
**Action:** Initialize authenticated Spotify session

```python
spotify = spotipy.Spotify(auth=SPOTIFY_ACCESS_TOKEN)

# Test connection:
current_user = spotify.current_user()
→ Returns user profile (validates token)
```

**Status Check:**
- ✅ Token valid (not expired)
- ✅ Spotify API reachable
- ✅ User profile retrieved

**If auth fails:**
- ❌ Log error, skip Spotify preference analysis, proceed with generic dark genre filtering

---

### [5] User Preference Analysis
**Time:** 2:03-2:05 AM
**Component:** `MadridEventsBot.get_user_dark_preferences()`
**Action:** Fetch and analyze user's Spotify data

**Sequence:**

```python
# Step 1: Fetch top 20 artists
GET /v1/me/top/artists?limit=20

# Step 2: Extract genres from each artist
for artist in top_artists:
    genres = artist['genres']
    # e.g., ['gothic rock', 'post-punk', 'darkwave']

# Step 3: Weight genres by dark relevance
DARK_GENRES_WEIGHT = {
    'gothic rock': 1.0,     ← highest
    'post-punk': 0.7,
    'indie rock': 0.3       ← lowest
}

dark_score = sum(DARK_GENRES_WEIGHT[genre] for genre in genres)

# Step 4: Sort top 10 genres by darkness affinity
Ranked genres:
  1. gothic rock (8.5 points)
  2. darkwave (7.2 points)
  3. post-punk (6.1 points)
  ...
```

**Output:** User preference profile
```json
{
  "genres": [
    ["gothic rock", 8.5],
    ["darkwave", 7.2],
    ["post-punk", 6.1]
  ],
  "top_artists": [
    "Bauhaus",
    "Siouxsie and the Banshees",
    "The Cure"
  ],
  "timestamp": "2026-03-27T02:05:00Z"
}
```

**Status Check:**
- ✅ Top 20 artists analyzed
- ✅ Top 10 dark genres ranked
- ✅ User profile saved to memory

---

### [6] Multi-Source Event Scraping
**Time:** 2:05-2:15 AM
**Component:** `MadridEventsBot.scrape_all_sources()`
**Action:** Scrape events from all 4 sources in parallel (or sequential)

#### Source 1: PlanetM (Madrid Nightclub)
```
GET https://www.planetm.es/
Parse HTML for: <article class="event">, <div class="evento">
Extract: title, date, venue
Filter: Dark keywords (gothic, metal, electronic, etc.)
Expected: 3-8 events
Timeout: 10s
```

**Sample output:**
```python
{
  'source': 'PlanetM',
  'title': 'Goth Night: Bauhaus & Sisters Tribute',
  'date': '2026-03-28',
  'url': 'https://www.planetm.es/',
  'relevance': 0.92
}
```

#### Source 2: GotiFiestas.com
```
GET https://www.gotifiestas.com/madrid
Parse HTML for: <div class="fiesta">, <li class="event-card">
Extract: title, date, venue, description
Filter: DARK_KEYWORDS check
Expected: 5-12 events
Timeout: 10s
```

#### Source 3: ConcertsMetal (es.concerts-metal.com)
```
GET https://es.concerts-metal.com/madrid
Parse HTML for: <div class="concert">, <tr class="event">
Extract: artist, date, venue
Filter: All metal genres (black metal, doom, death, post-metal)
Expected: 8-15 events
Timeout: 10s
```

#### Source 4: MadnessLive
```
GET https://www.madnesslive.es/es/
Parse HTML for: <article class="concierto">, <div class="event">
Extract: title, date, venue
Filter: Dark genre keywords
Expected: 5-10 events
Timeout: 10s
```

**Graceful Degradation:**
```
If PlanetM fails:
  ✅ Continue with GotiFiestas
  ✅ Continue with ConcertsMetal
  ✅ Continue with MadnessLive
  ⚠️ Log warning but don't crash

If 2+ sources fail:
  ⚠️ Still generate report with available data
  ℹ️ Note in report: "3 of 4 sources available"
```

**Total events collected:** 20-45 events across all sources

---

### [7] Event Filtering & Ranking
**Time:** 2:15-2:18 AM
**Component:** `MadridEventsBot._calculate_relevance()` & sorting
**Action:** Score and rank events by relevance to user preferences

**Relevance Algorithm:**

```python
def calculate_relevance(event_title, user_preferences):
    score = 0.5  # baseline

    # Match against dark genres (higher = better match)
    for genre, weight in user_preferences['genres'][:3]:
        if genre.lower() in event_title.lower():
            score += weight * 0.1  # Boost by genre match

    # Dark keyword bonus
    for keyword in ['goth', 'metal', 'dark', 'industrial']:
        if keyword in event_title.lower():
            score += 0.05

    return min(score, 1.0)  # Cap at 1.0
```

**Example Scoring:**

| Event | Base | Genre Match | Dark Keywords | Final Score |
|-------|------|-------------|---------------|-------------|
| "Goth Night: Bauhaus Tribute" | 0.5 | +0.18 (goth) | +0.05 | 0.73 🟡 |
| "Black Metal Festival Madrid" | 0.5 | +0.20 (metal) | +0.10 | 0.80 🟢 |
| "Indie Rock Show" | 0.5 | 0 | 0 | 0.50 ⚪ |

**Sort by relevance (descending):**
```
1. Black Metal Festival Madrid (0.80) 🟢
2. Goth Night: Bauhaus Tribute (0.73) 🟡
3. Darkwave Electronic Night (0.71) 🟡
4. Post-Rock Underground (0.62) 🟡
5. ...
```

**Keep top 10-15 events for report**

---

### [8] Report Generation
**Time:** 2:18-2:20 AM
**Component:** `MadridEventsBot.generate_report()`
**Action:** Format events into Telegram markdown

**Generated Report Template:**

```markdown
🎸 *Madrid Dark Events — This Week*
_Report from Thursday, March 27, 2026_

📊 *Your Genre Match:* Gothic Rock

*Top Events:*

⭐ *Black Metal Festival Madrid*
  📅 2026-03-29 | 📍 ConcertsMetal

✓ *Goth Night: Bauhaus Tribute*
  📅 2026-03-28 | 📍 PlanetM

✓ *Darkwave Electronic Night*
  📅 2026-03-30 | 📍 GotiFiestas

✓ *Post-Rock Underground Session*
  📅 2026-03-31 | 📍 MadnessLive

_...and 6 more events_
```

**Format Details:**
- ⭐ = High relevance (>0.75)
- ✓ = Medium relevance (0.5-0.75)
- Plain = Low relevance (<0.5, usually filtered out)

**Word Count:** 200-500 characters

---

### [9] Telegram Delivery
**Time:** 2:20-2:25 AM
**Component:** `mcp__nanoclaw__send_message()`
**Action:** Send report to NanoClaw group

```python
mcp__nanoclaw__send_message(
    text=report_markdown,
    sender="Madrid Events Bot"
)
```

**Telegram Message Routing:**
```
NanoClaw Task Agent
        ↓
mcp__nanoclaw__send_message()
        ↓
NanoClaw Message Queue
        ↓
Telegram Group
        ↓
All group members see bot message from "Madrid Events Bot"
```

**Status Check:**
- ✅ Message delivered to group
- ✅ Timestamp recorded (2:20 AM)
- ✅ No errors in delivery

---

## Task Completion
**Time:** 2:25 AM
**Total Duration:** ~25 minutes
**Status:** ✅ Success

**Memory Saved:**
- User preference profile (for future refinement)
- Scrape timestamps (to avoid duplicates next week)
- Any new sources discovered (for phase 2)

---

## Error Handling & Recovery

### Scenario 1: Spotify Token Expired
```
Attempt → Token fails
Action → Skip preference analysis
Fallback → Use generic dark genre list
Report → Still generated (just less personalized)
Status → ⚠️ Degraded mode
```

### Scenario 2: Network Timeout (Source Down)
```
Source: PlanetM → timeout after 10s
Action → Move to next source
Continue → GotiFiestas, ConcertsMetal, MadnessLive
Report → Shows "3 of 4 sources available"
Status → ✅ Partial success
```

### Scenario 3: Scraping HTML Structure Changed
```
HTML selectors no longer match
Events extracted: 0
Action → Log warning
Continue → Try alternative selectors
Report → "Limited results from [source]"
Status → ⚠️ Manual review needed for next run
```

### Scenario 4: All Sources Down
```
All 4 sources fail
Events found: 0
Report → "No events found this week. Check back next Thursday!"
Telegram → Message still sent
Status → ℹ️ Informational (not an error)
```

---

## Monitoring & Logs

**Log Locations:**
- `/tmp/madrid-events-bot-YYYY-MM-DD.log` (agent execution log)
- Console output during task run

**Log Entries:**

```
[2026-03-27 02:01:15] INFO - Starting Madrid Dark Events Bot...
[2026-03-27 02:02:30] INFO - Spotify auth: ✅ Token valid
[2026-03-27 02:03:45] INFO - User preferences: 20 artists analyzed
[2026-03-27 02:05:12] INFO - PlanetM: Found 5 events
[2026-03-27 02:08:33] INFO - GotiFiestas: Found 8 events
[2026-03-27 02:11:44] INFO - ConcertsMetal: Found 12 events
[2026-03-27 02:14:55] INFO - MadnessLive: Found 7 events
[2026-03-27 02:16:22] INFO - Total: 32 events, Top 10 ranked
[2026-03-27 02:18:33] INFO - Report generated: 312 chars
[2026-03-27 02:20:15] INFO - ✅ Message sent to Telegram
[2026-03-27 02:20:16] INFO - Task complete (19m 16s)
```

**View Logs:**
```bash
# During execution
tail -f /tmp/madrid-events-bot-*.log

# After execution
cat /tmp/madrid-events-bot-2026-03-27.log
```

---

## Next Steps / Future Enhancements

### Phase 2: Auto-Discover Sources
- Use Brave Search API to find new dark event websites
- Parse event feeds (RSS, JSON APIs)
- Learn from group feedback ("this was great!", "not interested")

### Phase 3: Venue Filtering
- Add proximity filter (show only events in central Madrid)
- Integrate with Google Maps API for travel time

### Phase 4: Ticket Integration
- Fetch ticket prices from Ticketmaster, Entradium
- Calculate cost efficiency (price per artist, duration, etc.)

### Phase 5: User Preferences Learning
- Remember which events user clicks on
- Adjust dark genre weights based on user engagement
- ML-based relevance scoring

---

## Rollback / Debugging

**If bot breaks on Thursday morning:**

1. **Check bot syntax:**
   ```bash
   python3 -m py_compile madrid_events_bot.py
   ```

2. **Test manually:**
   ```bash
   export SPOTIFY_ACCESS_TOKEN="your_token"
   python3 madrid_events_bot.py
   ```

3. **Check dependencies:**
   ```bash
   pip3 list | grep -E "spotipy|beautifulsoup"
   ```

4. **Test Spotify connection:**
   ```bash
   python3 -c "import spotipy; sp = spotipy.Spotify(auth='TOKEN'); print(sp.current_user())"
   ```

5. **Disable task temporarily:**
   ```bash
   /pause-task task-1774396219653-c8fv31
   ```

6. **Fix issues and re-enable:**
   ```bash
   /resume-task task-1774396219653-c8fv31
   ```

---

## Summary Table

| Phase | Component | Time | Action | Status |
|-------|-----------|------|--------|--------|
| [1] | Scheduler | 2:00 | Trigger task | ✅ |
| [2] | Environment | 2:01 | Load config | ✅ |
| [3] | Dependencies | 2:02 | pip install | ✅ |
| [4] | Spotify Auth | 2:03 | Authenticate | ✅ |
| [5] | Preferences | 2:05 | Analyze user | ✅ |
| [6] | Scraping | 2:15 | Fetch events (4 sources) | ✅ |
| [7] | Ranking | 2:18 | Score & sort | ✅ |
| [8] | Report | 2:20 | Generate markdown | ✅ |
| [9] | Delivery | 2:25 | Send to Telegram | ✅ |

**Total Duration:** ~25 minutes | **Success Rate Target:** 95%

---

**Last Updated:** 2026-03-24
**Bot Version:** 1.0
**Schedule:** Every Thursday 2:00 AM UTC
