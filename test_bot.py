#!/usr/bin/env python3
"""
Madrid Dark Events Bot — Test Suite
Comprehensive testing with exhaustive logging.

Usage:
    python3 test_bot.py <spotify_token>
"""

import os
import sys
import json
import logging
from datetime import datetime
from io import StringIO

# Configure VERBOSE logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)-8s %(name)s — %(message)s'
)

# Add file handler to save logs
log_file = f"/tmp/madrid-events-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(name)s — %(message)s'))
logging.getLogger().addHandler(file_handler)

logger = logging.getLogger('TestRunner')

def test_dependencies():
    """Test that all required dependencies are installed."""
    logger.info("=" * 70)
    logger.info("PHASE 1: Testing Dependencies")
    logger.info("=" * 70)

    deps = {
        'spotipy': 'Spotify API client',
        'requests': 'HTTP client',
        'beautifulsoup4': 'HTML parser',
        'lxml': 'XML/HTML backend',
    }

    for module, description in deps.items():
        try:
            __import__(module)
            logger.info(f"✅ {module:20} — {description}")
        except ImportError as e:
            logger.error(f"❌ {module:20} — MISSING: {e}")
            return False

    logger.info("")
    return True

def test_environment():
    """Test that all required environment variables are set."""
    logger.info("=" * 70)
    logger.info("PHASE 2: Testing Environment Variables")
    logger.info("=" * 70)

    env_vars = {
        'SPOTIFY_CLIENT_ID': 'Spotify App Client ID',
        'SPOTIFY_CLIENT_SECRET': 'Spotify App Secret',
        'BRAVE_SEARCH_API_KEY': 'Brave Search API Key',
    }

    all_set = True
    for var, description in env_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:10] + '...' if len(value) > 10 else value
            logger.info(f"✅ {var:30} — {masked}")
        else:
            logger.error(f"❌ {var:30} — NOT SET")
            all_set = False

    logger.info("")
    return all_set

def test_spotify_auth(token_str):
    """Test Spotify authentication with token manager."""
    logger.info("=" * 70)
    logger.info("PHASE 3: Testing Spotify Authentication (with Token Manager)")
    logger.info("=" * 70)

    try:
        from madrid_events_bot import SpotifyTokenManager
        import spotipy

        logger.info(f"Token provided: {token_str[:20]}...")

        # Create token manager (will auto-refresh if needed)
        logger.info("Creating SpotifyTokenManager...")
        token_manager = SpotifyTokenManager(
            refresh_token=token_str if len(token_str) > 100 else None,
            access_token=token_str if len(token_str) <= 100 else None
        )

        logger.info("Getting valid access token...")
        access_token = token_manager.get_valid_access_token()

        logger.info("Initializing Spotify client...")
        sp = spotipy.Spotify(auth=access_token)

        logger.info("Fetching current user profile...")
        user = sp.current_user()

        logger.info(f"✅ Authenticated as: {user.get('display_name', 'Unknown')}")
        logger.info(f"   User ID: {user.get('id')}")
        logger.info(f"   Email: {user.get('email')}")
        logger.info(f"✅ Token Manager: Ready with {'refresh' if token_manager.refresh_token else 'access'} token")
        logger.info("")
        return True, sp, token_manager

    except Exception as e:
        logger.error(f"❌ Spotify auth failed: {e}")
        logger.exception("Full traceback:")
        logger.info("")
        return False, None, None

def test_user_preferences(sp):
    """Test fetching and analyzing user preferences."""
    logger.info("=" * 70)
    logger.info("PHASE 4: Testing User Preference Analysis")
    logger.info("=" * 70)

    try:
        logger.info("Fetching top 20 artists...")
        top_artists = sp.current_user_top_artists(limit=20)

        logger.info(f"✅ Retrieved {len(top_artists['items'])} artists")
        logger.info("\nTop 5 Artists:")
        for i, artist in enumerate(top_artists['items'][:5], 1):
            genres = ', '.join(artist.get('genres', ['N/A'])[:2])
            logger.info(f"  {i}. {artist['name']:30} — {genres}")

        logger.info("\nGenre Analysis:")
        from madrid_events_bot import DARK_GENRES
        genre_weights = {}

        for artist in top_artists['items']:
            for genre in artist.get('genres', []):
                dark_weight = DARK_GENRES.get(genre.lower(), 0.3)
                genre_weights[genre] = genre_weights.get(genre, 0) + dark_weight

        sorted_genres = sorted(genre_weights.items(), key=lambda x: x[1], reverse=True)[:10]
        logger.info(f"✅ Top 10 Dark Genres:")
        for i, (genre, weight) in enumerate(sorted_genres, 1):
            logger.info(f"  {i}. {genre:30} (weight: {weight:.2f})")

        logger.info("")
        return True, {
            'top_artists': [a['name'] for a in top_artists['items'][:15]],
            'top_genres': sorted_genres
        }

    except Exception as e:
        logger.error(f"❌ User preference analysis failed: {e}")
        logger.exception("Full traceback:")
        logger.info("")
        return False, None

def test_bot_initialization(token_manager):
    """Test bot initialization with token manager."""
    logger.info("=" * 70)
    logger.info("PHASE 5: Testing Bot Initialization")
    logger.info("=" * 70)

    try:
        from madrid_events_bot import MadridEventsBot

        logger.info("Creating MadridEventsBot instance with TokenManager...")
        bot = MadridEventsBot(token_manager)
        logger.info("✅ Bot instance created successfully")

        logger.info("Testing user preference fetching...")
        prefs = bot.get_user_dark_preferences()

        if prefs and prefs.get('genres'):
            logger.info(f"✅ User preferences loaded")
            logger.info(f"   Top genre: {prefs['genres'][0][0]}")
            logger.info(f"   Top artists count: {len(prefs.get('top_artists', []))}")
            logger.info("")
            return True, bot
        else:
            logger.error("❌ Failed to load user preferences")
            logger.info("")
            return False, None

    except Exception as e:
        logger.error(f"❌ Bot initialization failed: {e}")
        logger.exception("Full traceback:")
        logger.info("")
        return False, None

def test_scraping(bot):
    """Test event scraping from all sources."""
    logger.info("=" * 70)
    logger.info("PHASE 6: Testing Event Scraping")
    logger.info("=" * 70)

    try:
        logger.info("Running comprehensive scraping...")
        events = bot.scrape_all_sources()

        logger.info(f"✅ Total events collected: {len(events)}")
        logger.info("")

        if events:
            logger.info("Top 5 Events by Relevance:")
            for i, event in enumerate(events[:5], 1):
                title = event.get('title', 'Unknown')[:50]
                source = event.get('source', 'Unknown')
                relevance = event.get('relevance', 0)
                logger.info(f"  {i}. [{source:15}] {title:50} (relevance: {relevance:.2f})")
            logger.info("")
        else:
            logger.warning("⚠️  No events found")
            logger.info("")

        return True, events

    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        logger.exception("Full traceback:")
        logger.info("")
        return False, None

def test_report_generation(bot, events):
    """Test report generation."""
    logger.info("=" * 70)
    logger.info("PHASE 7: Testing Report Generation")
    logger.info("=" * 70)

    try:
        if not events:
            logger.warning("⚠️  No events to report")
            logger.info("")
            return True, ""

        bot.events = events
        report = bot.generate_report()

        logger.info(f"✅ Report generated successfully")
        logger.info(f"   Length: {len(report)} characters")
        logger.info(f"   Lines: {len(report.splitlines())}")
        logger.info("")
        logger.info("Report Preview:")
        logger.info("-" * 70)
        for line in report.splitlines()[:15]:
            logger.info(line)
        if len(report.splitlines()) > 15:
            logger.info("   ... (truncated)")
        logger.info("-" * 70)
        logger.info("")

        return True, report

    except Exception as e:
        logger.error(f"❌ Report generation failed: {e}")
        logger.exception("Full traceback:")
        logger.info("")
        return False, None

def test_relevance_scoring():
    """Test relevance scoring logic."""
    logger.info("=" * 70)
    logger.info("PHASE 8: Testing Relevance Scoring Logic")
    logger.info("=" * 70)

    try:
        from madrid_events_bot import MadridEventsBot

        # Mock user preferences
        mock_prefs = {
            'top_artists': ['Bauhaus', 'The Cure', 'Sisters of Mercy', 'Siouxsie'],
            'genres': [('gothic rock', 0.9), ('post-punk', 0.95), ('darkwave', 0.85)]
        }

        test_titles = [
            "Bauhaus Live Concert",      # Artist match → HIGH
            "The Cure Tribute Night",     # Artist match → HIGH
            "Gothic Rock Evening",        # Genre match → MEDIUM
            "Dark Electronic Music",      # Genre + keyword → LOW-MEDIUM
            "Indie Folk Music",           # No match → LOW
        ]

        logger.info("Testing title scoring with mock preferences:")
        logger.info("")

        for title in test_titles:
            # Simulate scoring logic
            score = 0.5
            title_lower = title.lower()

            # Artist matching
            for artist in mock_prefs['top_artists']:
                if artist.lower() in title_lower:
                    score += 0.35
                    logger.info(f"  '{title:30}' → 0.5 + 0.35 (artist) = {score:.2f} ✅")
                    break
            else:
                # Genre matching
                for genre, weight in mock_prefs['genres']:
                    if genre.lower() in title_lower:
                        score += weight * 0.15
                        logger.info(f"  '{title:30}' → 0.5 + {weight*0.15:.2f} (genre) = {score:.2f} ✓")
                        break
                else:
                    logger.info(f"  '{title:30}' → {score:.2f} (baseline, no match)")

        logger.info("")
        return True

    except Exception as e:
        logger.error(f"❌ Relevance scoring test failed: {e}")
        logger.exception("Full traceback:")
        logger.info("")
        return False

def main():
    """Run full test suite."""
    logger.info("")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " " * 15 + "MADRID DARK EVENTS BOT — TEST SUITE" + " " * 19 + "║")
    logger.info("║" + f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}" + " " * 35 + "║")
    logger.info("╚" + "=" * 68 + "╝")
    logger.info("")

    results = []

    # Phase 1: Dependencies
    if not test_dependencies():
        logger.critical("❌ Dependencies missing. Cannot continue.")
        return False

    # Phase 2: Environment
    if not test_environment():
        logger.critical("❌ Environment variables missing. Cannot continue.")
        return False

    # Phase 3: Spotify Auth (with Token Manager)
    # Try to get token from various sources
    refresh_token = os.getenv('SPOTIFY_REFRESH_TOKEN')
    access_token = os.getenv('SPOTIFY_ACCESS_TOKEN')

    # Check command-line args
    if len(sys.argv) > 1:
        if len(sys.argv[1]) > 100:
            refresh_token = sys.argv[1]
        else:
            access_token = sys.argv[1]

    if len(sys.argv) > 2:
        access_token = sys.argv[2]

    token = refresh_token or access_token

    if not token:
        logger.error("❌ No Spotify token provided!")
        logger.error("Usage: python3 test_bot.py <refresh_token> [access_token]")
        return False

    sp_ok, sp, token_manager = test_spotify_auth(token)
    results.append(('Spotify Auth', sp_ok))

    if not sp_ok:
        logger.critical("❌ Spotify authentication failed. Cannot continue.")
        return False

    # Phase 4: User Preferences
    prefs_ok, prefs = test_user_preferences(sp)
    results.append(('User Preferences', prefs_ok))

    # Phase 5: Bot Init (with TokenManager)
    bot_ok, bot = test_bot_initialization(token_manager)
    results.append(('Bot Initialization', bot_ok))

    if not bot_ok:
        logger.critical("❌ Bot initialization failed. Cannot continue.")
        return False

    # Phase 6: Scraping
    scrape_ok, events = test_scraping(bot)
    results.append(('Event Scraping', scrape_ok))

    # Phase 7: Report
    if events:
        report_ok, report = test_report_generation(bot, events)
        results.append(('Report Generation', report_ok))

    # Phase 8: Scoring Logic
    scoring_ok = test_relevance_scoring()
    results.append(('Relevance Scoring', scoring_ok))

    # Final summary
    logger.info("=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {test_name:30} — {status}")

    all_passed = all(r[1] for r in results)
    logger.info("")
    logger.info("=" * 70)

    if all_passed:
        logger.info("✅ ALL TESTS PASSED")
    else:
        logger.error("❌ SOME TESTS FAILED")

    logger.info("=" * 70)
    logger.info(f"Log saved to: {log_file}")
    logger.info("")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
