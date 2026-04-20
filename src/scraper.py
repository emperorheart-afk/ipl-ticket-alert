"""
District.in IPL Ticket Scraper
Monitors ticket availability and status changes
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import re
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistrictIPLScraper:
    def __init__(self):
        self.base_url = "https://www.district.in/events/ipl-ticket-booking"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
    def scrape_all_matches(self) -> List[Dict]:
        """Scrape all IPL matches"""
        try:
            logger.info(f"Scraping: {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            matches = []
            
            match_cards = soup.find_all('div', class_=re.compile(r'card|event', re.I))
            if not match_cards:
                match_cards = soup.find_all(['div', 'article'], recursive=True)
            
            logger.info(f"Found {len(match_cards)} cards")
            
            for card in match_cards:
                try:
                    match_data = self._parse_match_card(card)
                    if match_data and match_data.get('teams'):
                        matches.append(match_data)
                except:
                    continue
            
            logger.info(f"Parsed {len(matches)} matches")
            return matches
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
    
    def _parse_match_card(self, card) -> Optional[Dict]:
        """Parse match card"""
        try:
            card_text = card.get_text(separator=' ', strip=True)
            
            team_patterns = [
                'Chennai Super Kings', 'CSK',
                'Mumbai Indians', 'MI',
                'Royal Challengers Bangalore', 'RCB',
                'Kolkata Knight Riders', 'KKR',
                'Delhi Capitals', 'DC',
                'Rajasthan Royals', 'RR',
                'Punjab Kings', 'PBKS',
                'Sunrisers Hyderabad', 'SRH',
                'Gujarat Titans', 'GT',
                'Lucknow Super Giants', 'LSG'
            ]
            
            found_teams = []
            for pattern in team_patterns:
                if pattern in card_text and pattern not in found_teams:
                    found_teams.append(pattern)
                    if len(found_teams) == 2:
                        break
            
            if len(found_teams) < 2:
                return None
            
            teams = ' vs '.join(found_teams[:2])
            
            # Date
            date_match = re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', card_text)
            date = f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}" if date_match else "Date TBD"
            
            # Time
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', card_text)
            match_time = time_match.group(0) if time_match else "Time TBD"
            
            # Stadium
            stadium_match = re.search(r'([\w\s]+Stadium)', card_text)
            stadium = stadium_match.group(1).strip() if stadium_match else "Stadium TBD"
            
            status = self._detect_status(card)
            
            book_link = None
            book_btn = card.find('a', href=True)
            if book_btn:
                book_link = book_btn['href']
                if not book_link.startswith('http'):
                    book_link = f"https://www.district.in{book_link}"
            
            return {
                'teams': teams,
                'date': date,
                'stadium': stadium,
                'time': match_time,
                'status': status,
                'booking_link': book_link,
                'timestamp': datetime.now().isoformat(),
                'source': 'district.in'
            }
        except:
            return None
    
    def _detect_status(self, card) -> str:
        """Detect status"""
        card_text = card.get_text().lower()
        
        if 'sale is live' in card_text or 'book tickets' in card_text:
            return 'AVAILABLE'
        elif 'sale starts soon' in card_text or 'notify me' in card_text:
            return 'COMING_SOON'
        elif 'coming soon' in card_text:
            return 'NOT_YET_ANNOUNCED'
        elif 'sold out' in card_text:
            return 'SOLD_OUT'
        else:
            return 'UNKNOWN'
    
    def filter_matches(self, matches: List[Dict], team: str = None, city: str = None) -> List[Dict]:
        """Filter matches"""
        filtered = matches
        
        if team and team.lower() != 'any':
            filtered = [m for m in filtered if team.lower() in m['teams'].lower()]
        
        if city and city.lower() != 'any':
            filtered = [m for m in filtered if city.lower() in m['stadium'].lower()]
        
        return filtered
    
    def save_results(self, matches: List[Dict], filepath: str = "data/tickets.json"):
        """Save results"""
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    'last_updated': datetime.now().isoformat(),
                    'total_matches': len(matches),
                    'matches': matches
                }, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False
