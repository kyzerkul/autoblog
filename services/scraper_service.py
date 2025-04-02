#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube Scraper Service - Alternative to YouTube API
No API key required, but less reliable and may break if YouTube changes their UI
"""

import re
import json
import random
import logging
import requests
import urllib.parse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ScraperService:
    """Service for scraping YouTube data without using the API"""
    
    def __init__(self):
        """Initialize the scraper service"""
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        ]
        self.session = requests.Session()
    
    def _get_random_user_agent(self):
        """Return a random user agent from the list"""
        return random.choice(self.user_agents)
    
    def search_videos(self, query, max_results=10, published_after=None):
        """
        Search for YouTube videos without using the API
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            published_after (datetime): Filter videos published after this date
            
        Returns:
            list: List of video information dictionaries
        """
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        if published_after:
            # Add a filter for upload date if specified
            # Note: This doesn't precisely match the date but uses YouTube's predefined filters
            days_ago = (datetime.now() - published_after).days
            if days_ago <= 1:
                search_url += "&sp=CAISAhAB"  # Last 24 hours
            elif days_ago <= 7:
                search_url += "&sp=CAISAhAC"  # This week
            elif days_ago <= 30:
                search_url += "&sp=CAISAhAD"  # This month
            elif days_ago <= 365:
                search_url += "&sp=CAISAhAE"  # This year
        
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        }
        
        try:
            logger.info(f"Searching YouTube for '{query}'")
            response = self.session.get(search_url, headers=headers)
            response.raise_for_status()
            
            # YouTube loads search results via JavaScript and stores initial data in a JSON variable
            # We need to extract this data from the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract video information from the page
            videos = []
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string and 'var ytInitialData' in script.string:
                    # Extract the JSON data
                    data_str = script.string.split('var ytInitialData = ')[1].split(';</script>')[0]
                    json_data = json.loads(data_str)
                    
                    # Navigate the complex JSON structure to find video results
                    try:
                        contents = json_data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
                        
                        for content in contents:
                            if 'itemSectionRenderer' in content:
                                items = content['itemSectionRenderer']['contents']
                                
                                for item in items:
                                    if 'videoRenderer' in item:
                                        video_data = item['videoRenderer']
                                        
                                        # Extract basic video information
                                        video_id = video_data.get('videoId', '')
                                        title = video_data.get('title', {}).get('runs', [{}])[0].get('text', 'Untitled Video')
                                        
                                        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                                        
                                        # Extract channel information
                                        channel_title = ''
                                        channel_id = ''
                                        if 'ownerText' in video_data:
                                            channel_title = video_data['ownerText'].get('runs', [{}])[0].get('text', '')
                                        
                                        if 'channelId' in video_data:
                                            channel_id = video_data.get('channelId', '')
                                            
                                        # Extract published date (this is usually a relative date like "1 month ago")
                                        published_text = ''
                                        if 'publishedTimeText' in video_data:
                                            published_text = video_data['publishedTimeText'].get('simpleText', '')
                                        
                                        # Create video info dictionary
                                        video_info = {
                                            'id': video_id,
                                            'url': f"https://www.youtube.com/watch?v={video_id}",
                                            'title': title,
                                            'channel_title': channel_title,
                                            'channel_id': channel_id,
                                            'published_text': published_text,
                                            'thumbnail_url': thumbnail_url
                                        }
                                        
                                        videos.append(video_info)
                                        
                                        if len(videos) >= max_results:
                                            break
                    except (KeyError, IndexError) as e:
                        logger.warning(f"Error extracting video data: {str(e)}")
                        continue
                    
                    break  # Exit after processing the first matching script
            
            return videos[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching YouTube: {str(e)}")
            return []
    
    def get_feed_videos(self, feed_url, max_results=10):
        """
        Get videos from a YouTube RSS feed
        
        Args:
            feed_url (str): YouTube RSS feed URL
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of video information dictionaries
        """
        try:
            logger.info(f"Fetching videos from RSS feed: {feed_url}")
            
            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Accept': 'application/xml, text/xml, */*;q=0.9',
            }
            
            response = self.session.get(feed_url, headers=headers)
            response.raise_for_status()
            
            # Parse the XML
            soup = BeautifulSoup(response.text, 'xml')
            
            videos = []
            entries = soup.find_all('entry')
            
            for entry in entries[:max_results]:
                try:
                    # Extract video information from the entry
                    video_id = entry.find('yt:videoId').text
                    title = entry.find('title').text
                    channel_title = entry.find('author').find('name').text
                    published = entry.find('published').text
                    
                    # Extract thumbnail URL (construct standard URL since RSS doesn't provide it)
                    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                    
                    # Create video info dictionary
                    video_info = {
                        'id': video_id,
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'title': title,
                        'channel_title': channel_title,
                        'published_text': published,
                        'thumbnail_url': thumbnail_url
                    }
                    
                    videos.append(video_info)
                    
                except Exception as e:
                    logger.warning(f"Error extracting video data from feed: {str(e)}")
                    continue
            
            return videos
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {str(e)}")
            return []
    
    def get_trending_videos(self, category="default", max_results=10):
        """
        Get trending videos from YouTube without API
        
        Args:
            category (str): Category for trending videos
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of video information dictionaries
        """
        try:
            trending_url = "https://www.youtube.com/feed/trending"
            
            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            }
            
            response = self.session.get(trending_url, headers=headers)
            response.raise_for_status()
            
            # Similar extraction logic as search_videos
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract video information from the page
            videos = []
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string and 'var ytInitialData' in script.string:
                    # Extract the JSON data
                    data_str = script.string.split('var ytInitialData = ')[1].split(';</script>')[0]
                    json_data = json.loads(data_str)
                    
                    # The structure for trending videos is different, so adapt the extraction logic
                    try:
                        # Navigate through the JSON to find trending videos
                        # This is a simplification and may need adaptation based on YouTube's structure
                        contents = json_data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents']
                        
                        for content in contents:
                            if 'itemSectionRenderer' in content:
                                items = content['itemSectionRenderer']['contents']
                                
                                for item in items:
                                    if 'shelfRenderer' in item:
                                        videos_items = item['shelfRenderer']['content']['expandedShelfContentsRenderer']['items']
                                        
                                        for video_item in videos_items:
                                            if 'videoRenderer' in video_item:
                                                video_data = video_item['videoRenderer']
                                                
                                                # Extract basic video information, similar to search_videos
                                                video_id = video_data.get('videoId', '')
                                                title = video_data.get('title', {}).get('runs', [{}])[0].get('text', 'Untitled Video')
                                                
                                                thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                                                
                                                # Extract channel information
                                                channel_title = ''
                                                if 'ownerText' in video_data:
                                                    channel_title = video_data['ownerText'].get('runs', [{}])[0].get('text', '')
                                                
                                                # Extract published date
                                                published_text = ''
                                                if 'publishedTimeText' in video_data:
                                                    published_text = video_data['publishedTimeText'].get('simpleText', '')
                                                
                                                # Create video info dictionary
                                                video_info = {
                                                    'id': video_id,
                                                    'url': f"https://www.youtube.com/watch?v={video_id}",
                                                    'title': title,
                                                    'channel_title': channel_title,
                                                    'published_text': published_text,
                                                    'thumbnail_url': thumbnail_url
                                                }
                                                
                                                videos.append(video_info)
                                                
                                                if len(videos) >= max_results:
                                                    break
                    except (KeyError, IndexError) as e:
                        logger.warning(f"Error extracting trending video data: {str(e)}")
                        continue
                    
                    break  # Exit after processing the first matching script
            
            return videos[:max_results]
            
        except Exception as e:
            logger.error(f"Error fetching trending videos: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = ScraperService()
    
    # Example search
    results = scraper.search_videos("python tutorial", max_results=5)
    for video in results:
        print(f"Title: {video['title']}")
        print(f"URL: {video['url']}")
        print(f"Channel: {video['channel_title']}")
        print(f"Published: {video['published_text']}")
        print("---")
    
    # Example trending videos
    trending = scraper.get_trending_videos(max_results=5)
    print("\nTrending Videos:")
    for video in trending:
        print(f"Title: {video['title']}")
        print(f"URL: {video['url']}")
        print("---")
