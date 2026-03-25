#!/usr/bin/env python3
"""
Madrid Dark Events Bot
Weekly discovery of dark/gothic/metal events in Madrid based on Spotify preferences.

Runs: Thursday 2 AM via NanoClaw scheduler
Reports: Posts to Telegram group
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import requests
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpotifyTokenManager:
    """Manages Spotify tokens with automatic refresh capability."""

    def __init__(self, refresh_token: Optional[str] = None, access_token: Optional[str] = None):
        """
        Initialize token manager.

        Args:
            refresh_token: Long-lived refresh token (preferred)
            access_token: Short-lived access token (fallback)
        """
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.token_expires_at = None

        if not self.client_id or not self.client_secret:
            raise ValueError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET")

    def get_valid_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns the current access token, refreshing from refresh_token if expired.
        """
        # If we have a refresh token, use OAuth to auto-renew
        if self.refresh_token:
            return self._refresh_access_token()

        # Fallback: use provided access token (will expire after 1 hour)
        if self.access_token:
            logger.warning("Using access token without refresh - will expire in ~1 hour")
            return self.access_token

        raise ValueError("No valid tokens provided")

    def _refresh_access_token(self) -> str:
        """Refresh access token using refresh token."""
        try:
            logger.info("🔄 Refreshing Spotify access token...")

            # Use Spotify's token endpoint
            auth_url = "https://accounts.spotify.com/api/token"
            payload = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }

            response = requests.post(auth_url, data=payload, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires_at = datetime.now() + timedelta(
                seconds=token_data.get('expires_in', 3600)
            )

            logger.info(f"✅ Token refreshed. Expires at: {self.token_expires_at}")
            return self.access_token

        except Exception as e:
            logger.error(f"❌ Failed to refresh token: {e}")
            raise

    @staticmethod
    def from_env_or_args(args: list) -> 'SpotifyTokenManager':
        """
        Create TokenManager from environment or command-line arguments.

        Priority:
        1. SPOTIFY_REFRESH_TOKEN env var (best)
        2. First argument to script (refresh token)
        3. SPOTIFY_ACCESS_TOKEN env var (fallback)
        4. Second argument to script (access token fallback)
        """
        refresh_token = os.getenv('SPOTIFY_REFRESH_TOKEN')
        access_token = os.getenv('SPOTIFY_ACCESS_TOKEN')

        # Check command-line arguments
        if len(args) > 1:
            # First arg is likely refresh token (long)
            if len(args[1]) > 100:
                refresh_token = args[1]
            else:
                access_token = args[1]

        if len(args) > 2:
            access_token = args[2]

        if not refresh_token and not access_token:
            raise ValueError(
                "No Spotify tokens provided!\n"
                "Usage: python3 madrid_events_bot.py <refresh_token> [access_token]\n"
                "Or set: SPOTIFY_REFRESH_TOKEN or SPOTIFY_ACCESS_TOKEN env vars"
            )

        return SpotifyTokenManager(refresh_token=refresh_token, access_token=access_token)

# Dark music genres and keywords
DARK_GENRES = {
    'gothic': 0.9,
    'gothic rock': 1.0,
    'darkwave': 0.95,
    'black metal': 1.0,
    'doom metal': 1.0,
    'death metal': 0.8,
    'post-metal': 1.0,
    'post-rock': 0.7,
    'post-punk': 0.95,  # Added post-punk
    'shoegaze': 0.6,
    'neofolk': 0.95,  # Increased weight from 0.85 to 0.95
    'dark electronic': 0.9,
    'industrial': 0.8,
    'ethereal wave': 0.85,
    'cold wave': 0.9,
}

class MadridEventsBot:
    def __init__(self, token_manager: SpotifyTokenManager):
        """
        Initialize the bot with a token manager.

        Args:
            token_manager: SpotifyTokenManager instance
        """
        self.token_manager = token_manager

        # Get valid access token (auto-refreshes if needed)
        access_token = token_manager.get_valid_access_token()
        self.spotify = spotipy.Spotify(auth=access_token)

        self.events = []
        self.user_preferences = {}

    def get_user_dark_preferences(self) -> Dict:
        """Analyze user's Spotify top tracks/artists to infer dark music preferences."""
        try:
            # Get top artists
            top_artists = self.spotify.current_user_top_artists(limit=20)
            top_genres = {}

            for artist in top_artists['items']:
                for genre in artist.get('genres', []):
                    # Calculate genre affinity based on DARK_GENRES mapping
                    dark_weight = DARK_GENRES.get(genre.lower(), 0.3)
                    top_genres[genre] = top_genres.get(genre, 0) + dark_weight

            # Sort by darkness affinity
            sorted_genres = sorted(top_genres.items(), key=lambda x: x[1], reverse=True)[:10]

            self.user_preferences = {
                'genres': sorted_genres,
                'timestamp': datetime.now().isoformat(),
                'top_artists': [a['name'] for a in top_artists['items'][:15]]  # Extended to 15 for better matching
            }

            top_artist_names = ', '.join([a['name'] for a in top_artists['items'][:3]])
            logger.info(f"User top artists: {top_artist_names}")
            logger.info(f"User dark genre affinity: {sorted_genres[:3]}")
            return self.user_preferences

        except Exception as e:
            logger.error(f"Error fetching Spotify preferences: {e}")
            return {}

    def scrape_planetm(self) -> List[Dict]:
        """Fetch PlanetM (PLANET M SCIFI & ROCK'N'ROLL BAR) events from Instagram/Facebook via Brave Search."""
        events = []
        try:
            brave_api_key = os.getenv('BRAVE_SEARCH_API_KEY')
            if not brave_api_key:
                logger.warning("BRAVE_SEARCH_API_KEY not set, skipping PlanetM")
                return []

            headers = {'Accept': 'application/json', 'X-Subscription-Token': brave_api_key}

            # Search PlanetM bar events via Brave Search (lightweight alternative to HTML scraping)
            search_queries = [
                "planetm_bar instagram events madrid scifi rock",
                "PLANET M bar rock and roll madrid concerts",
                "facebook.com/planetmongo events madrid"
            ]

            for query in search_queries:
                try:
                    response = requests.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers=headers,
                        params={'q': query, 'count': 5, 'text_format': 'plain'},
                        timeout=5
                    )

                    if response.status_code == 200:
                        results = response.json().get('web', [])
                        for result in results[:3]:
                            title = result.get('title', '')
                            desc = result.get('description', '')

                            # Look for event-related keywords in results
                            if any(kw in title.lower() or kw in desc.lower()
                                   for kw in ['event', 'concert', 'night', 'party', 'live', 'show', 'dj']):
                                events.append({
                                    'source': 'PlanetM (Bar)',
                                    'title': title[:80],
                                    'date': 'Check @planetm_bar on Instagram',
                                    'url': result.get('url', 'https://instagram.com/planetm_bar'),
                                    'relevance': 0.85
                                })
                                if len(events) >= 4:
                                    break
                except Exception as e:
                    logger.debug(f"Brave search query failed: {e}")

                if len(events) >= 4:
                    break

            logger.info(f"PlanetM (via Brave Search): Found {len(events)} events")

        except Exception as e:
            logger.warning(f"Error fetching PlanetM events: {e}")

        return events

    def scrape_gotifiestas(self) -> List[Dict]:
        """Scrape dark events from gotifiestas.com via lightweight scraping."""
        events = []
        try:
            url = "https://www.gotifiestas.com/madrid"
            headers = {'User-Agent': 'Mozilla/5.0 (Dark Events Bot)'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for event cards
            event_cards = soup.find_all(['div', 'li'], class_=['event-card', 'fiesta'])

            for card in event_cards[:8]:  # Get up to 8 events
                title_elem = card.find(['h3', 'h2'])
                date_elem = card.find(['span', 'p'], class_=['date', 'fecha'])

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    # Filter for dark keywords
                    if self._is_dark_event(title):
                        events.append({
                            'source': 'GotiFiestas',
                            'title': title,
                            'date': date_elem.get_text(strip=True) if date_elem else 'TBD',
                            'url': url,
                            'relevance': self._calculate_relevance(title)
                        })

            logger.info(f"GotiFiestas: Found {len(events)} dark events")
        except Exception as e:
            logger.warning(f"Error scraping GotiFiestas: {e}")

        return events

    def scrape_concerts_metal(self) -> List[Dict]:
        """Scrape metal concerts from es.concerts-metal.com."""
        events = []
        try:
            url = "https://es.concerts-metal.com/madrid"
            headers = {'User-Agent': 'Mozilla/5.0 (Dark Events Bot)'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for concert listings
            concerts = soup.find_all(['div', 'tr'], class_=['concert', 'event'])

            for concert in concerts[:10]:
                artist_elem = concert.find(['h2', 'h3', 'td'])
                date_elem = concert.find(['span', 'p'], class_=['date', 'fecha'])
                venue_elem = concert.find(['p', 'span'], class_=['venue', 'lugar'])

                if artist_elem:
                    events.append({
                        'source': 'ConcertsMetal',
                        'title': artist_elem.get_text(strip=True),
                        'date': date_elem.get_text(strip=True) if date_elem else 'TBD',
                        'venue': venue_elem.get_text(strip=True) if venue_elem else 'Madrid',
                        'url': url,
                        'type': 'concert'
                    })

            logger.info(f"ConcertsMetal: Found {len(events)} metal concerts")
        except Exception as e:
            logger.warning(f"Error scraping ConcertsMetal: {e}")

        return events

    def scrape_madnesslive(self) -> List[Dict]:
        """Scrape events from madnesslive.com."""
        events = []
        try:
            url = "https://www.madnesslive.es/es/"
            headers = {'User-Agent': 'Mozilla/5.0 (Dark Events Bot)'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for event listings
            event_items = soup.find_all(['div', 'article'], class_=['event', 'concierto'])

            for item in event_items[:10]:
                title_elem = item.find(['h2', 'h3'])
                date_elem = item.find(['span', 'p'], class_=['date', 'fecha', 'when'])

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if self._is_dark_event(title):
                        events.append({
                            'source': 'MadnessLive',
                            'title': title,
                            'date': date_elem.get_text(strip=True) if date_elem else 'TBD',
                            'url': url,
                            'relevance': self._calculate_relevance(title)
                        })

            logger.info(f"MadnessLive: Found {len(events)} events")
        except Exception as e:
            logger.warning(f"Error scraping MadnessLive: {e}")

        return events

    def _is_dark_event(self, title: str) -> bool:
        """Check if event title contains dark/gothic/metal keywords."""
        dark_keywords = [
            'goth', 'dark', 'metal', 'black', 'doom', 'post-rock', 'post-punk', 'shoegaze',
            'neofolk', 'electronic', 'industrial', 'wave', 'coldwave', 'post-metal',
            'doom metal', 'gothic rock', 'darkwave', 'ethereal', 'punk'
        ]
        title_lower = title.lower()
        return any(kw in title_lower for kw in dark_keywords)

    def _calculate_relevance(self, event_title: str) -> float:
        """
        Calculate relevance score based on user preferences (0-1).

        Strategy:
        1. Check if event title contains user's top artists (high weight)
        2. Check if event title contains dark genres (medium weight)
        3. Check dark keywords (low weight)
        """
        score = 0.5  # baseline
        title_lower = event_title.lower()

        # ✅ Strategy 1: Match user's top artists (HIGHEST PRIORITY)
        # Events with the user's favorite artists are most relevant
        top_artists = self.user_preferences.get('top_artists', [])
        for artist_name in top_artists[:10]:  # Check top 10 artists
            artist_lower = artist_name.lower()
            if artist_lower in title_lower:
                score += 0.35  # High boost for artist match
                logger.debug(f"Artist match: {artist_name} in '{event_title}' → +0.35")
                break  # Only count first artist match

        # ✅ Strategy 2: Match user's top dark genres (MEDIUM PRIORITY)
        # If no artist match, genre matching provides context about event style
        if score == 0.5:  # Only if no artist match found
            for genre, weight in self.user_preferences.get('genres', [])[:5]:
                genre_lower = genre.lower()
                if genre_lower in title_lower:
                    score += (weight * 0.15)  # Scale weight to boost
                    logger.debug(f"Genre match: {genre} (weight {weight}) in '{event_title}' → +{weight*0.15:.2f}")
                    break  # Only count first genre match

        # ✅ Strategy 3: Dark keyword bonus (LOW PRIORITY, supplementary)
        dark_keywords_bonus = {
            'goth': 0.08,
            'metal': 0.10,
            'dark': 0.05,
            'black metal': 0.15,
            'doom': 0.10,
            'post-punk': 0.12,
            'neofolk': 0.12,
            'industrial': 0.08,
        }
        for keyword, bonus in dark_keywords_bonus.items():
            if keyword in title_lower:
                score += bonus
                logger.debug(f"Keyword match: '{keyword}' → +{bonus}")
                break

        return min(score, 1.0)

    def scrape_all_sources(self) -> List[Dict]:
        """Scrape all event sources."""
        logger.info("🔍 Starting event scraping...")

        all_events = []
        all_events.extend(self.scrape_planetm())
        all_events.extend(self.scrape_gotifiestas())
        all_events.extend(self.scrape_concerts_metal())
        all_events.extend(self.scrape_madnesslive())

        # Sort by relevance if available
        all_events.sort(key=lambda e: e.get('relevance', 0.5), reverse=True)

        logger.info(f"✅ Total events found: {len(all_events)}")
        return all_events

    def generate_report(self) -> str:
        """Generate Telegram-formatted report."""
        if not self.events:
            return "_No events found this week. Stay tuned!_"

        report = []
        report.append("🎸 *Madrid Dark Events — This Week*")
        report.append(f"_Report from {datetime.now().strftime('%A, %B %d, %Y')}_")
        report.append("")

        # Add user preferences summary
        if self.user_preferences.get('genres'):
            top_genre = self.user_preferences['genres'][0][0]
            report.append(f"📊 *Your Genre Match:* {top_genre.title()}")
            report.append("")

        # Add top events
        report.append("*Top Events:*")
        for i, event in enumerate(self.events[:5], 1):
            title = event.get('title', 'Unknown Event')
            date = event.get('date', 'TBD')
            source = event.get('source', 'Unknown')
            relevance = event.get('relevance', 0.5)

            # Emoji based on relevance
            emoji = '⭐' if relevance > 0.7 else '✓'

            report.append(f"{emoji} *{title}*")
            report.append(f"  📅 {date} | 📍 {source}")
            report.append("")

        if len(self.events) > 5:
            report.append(f"_...and {len(self.events) - 5} more events_")

        return "\n".join(report)

    def run(self):
        """Main bot execution."""
        try:
            logger.info("Starting Madrid Dark Events Bot...")

            # Step 1: Get user preferences
            self.get_user_dark_preferences()

            # Step 2: Scrape all sources
            self.events = self.scrape_all_sources()

            # Step 3: Generate report
            report = self.generate_report()

            logger.info(f"Report generated: {len(report)} chars")
            return report

        except Exception as e:
            logger.error(f"Bot execution error: {e}")
            return f"❌ Error running bot: {str(e)}"

def main():
    """Main entry point for the Madrid Dark Events Bot."""
    try:
        # Create token manager (handles refresh automatically)
        token_manager = SpotifyTokenManager.from_env_or_args(sys.argv)

        logger.info("🎵 Madrid Dark Events Bot Starting...")
        logger.info(f"Using Spotify credentials (Client ID: {token_manager.client_id[:10]}...)")

        # Run bot
        bot = MadridEventsBot(token_manager)
        report = bot.run()

        # Print report (for logging/debugging)
        print(report)

        # In NanoClaw context, send to Telegram via mcp__nanoclaw__send_message
        # This would be handled by the scheduler task

        return True

    except Exception as e:
        logger.error(f"❌ Bot failed: {e}")
        logger.exception("Full traceback:")
        return False

if __name__ == "__main__":
    main()
