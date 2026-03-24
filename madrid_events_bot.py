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
from typing import List, Dict, Tuple
import requests
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    'shoegaze': 0.6,
    'neofolk': 0.85,
    'dark electronic': 0.9,
    'industrial': 0.8,
    'ethereal wave': 0.85,
    'cold wave': 0.9,
}

class MadridEventsBot:
    def __init__(self, spotify_token: str):
        self.spotify = spotipy.Spotify(auth=spotify_token)
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
                'top_artists': [a['name'] for a in top_artists['items'][:5]]
            }

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
        """Scrape dark events from gotifiestas.com."""
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
            'goth', 'dark', 'metal', 'black', 'doom', 'post-rock', 'shoegaze',
            'neofolk', 'electronic', 'industrial', 'wave', 'coldwave', 'post-metal',
            'doom metal', 'gothic rock', 'darkwave', 'ethereal'
        ]
        title_lower = title.lower()
        return any(kw in title_lower for kw in dark_keywords)

    def _calculate_relevance(self, event_title: str) -> float:
        """Calculate relevance score based on user preferences (0-1)."""
        score = 0.5  # baseline
        title_lower = event_title.lower()

        # Check against user's top genres
        for genre, weight in self.user_preferences.get('genres', [])[:3]:
            if genre.lower() in title_lower:
                score += weight * 0.1

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
    # Get Spotify token from environment or argument
    spotify_token = os.getenv('SPOTIFY_ACCESS_TOKEN')
    if not spotify_token and len(sys.argv) > 1:
        spotify_token = sys.argv[1]

    if not spotify_token:
        print("ERROR: Spotify access token required!")
        print("Usage: python3 madrid_events_bot.py <token>")
        print("Or set SPOTIFY_ACCESS_TOKEN environment variable")
        sys.exit(1)

    # Run bot
    bot = MadridEventsBot(spotify_token)
    report = bot.run()

    # Print report (for logging/debugging)
    print(report)

    # In NanoClaw context, send to Telegram via mcp__nanoclaw__send_message
    # This would be handled by the scheduler task

if __name__ == "__main__":
    main()
