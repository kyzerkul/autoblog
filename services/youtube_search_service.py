import os
import json
import random
import logging
import requests
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

from .youtube_service import YouTubeService
from .mistral_service import MistralService
from .wordpress_service import WordPressService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("youtube_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("YouTube Search Service")

class YouTubeSearchService:
    """Service for searching YouTube videos and generating articles from them"""
    
    def __init__(self):
        """Initialize the YouTube search service"""
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            logger.warning("YouTube API key not configured in .env file")
        
        self.youtube_service = YouTubeService()
        self.mistral_service = MistralService()
        self.wordpress_service = WordPressService()
        
        # Load processed videos history
        self.history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'processed_videos.json')
        self.processed_videos = self._load_processed_videos()
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
    
    def _load_processed_videos(self):
        """Load the list of processed videos from storage"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading processed videos: {str(e)}")
            return []
    
    def _save_processed_videos(self):
        """Save the list of processed videos to storage"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_videos, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed videos: {str(e)}")
    
    def search_videos(self, query, max_results=5, published_after=None):
        """
        Search for YouTube videos based on a query
        
        Parameters:
        - query: Search term
        - max_results: Maximum number of results to return
        - published_after: Only return videos published after this date (ISO format string)
        
        Returns:
        - List of video details
        """
        if not self.api_key:
            logger.error("YouTube API key is required for search")
            return []
        
        try:
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            
            # Build request parameters
            search_params = {
                'q': query,
                'type': 'video',
                'part': 'snippet',
                'maxResults': max_results,
                'relevanceLanguage': 'en',  # Or 'fr' for French
                'videoCaption': 'closedCaption',  # Only videos with captions
                'fields': 'items(id(videoId),snippet(title,description,channelTitle,publishedAt))'
            }
            
            # Add published_after filter if provided
            if published_after:
                search_params['publishedAfter'] = published_after
            
            # Execute search
            search_response = youtube.search().list(**search_params).execute()
            
            # Process results
            videos = []
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Skip already processed videos
                if video_id in self.processed_videos:
                    logger.info(f"Skipping already processed video: {video_url}")
                    continue
                
                # Check if the video has a transcript
                has_transcript = self._check_video_transcript(video_url)
                if not has_transcript:
                    logger.info(f"Skipping video without transcript: {video_url}")
                    continue
                
                # Add to results
                videos.append({
                    'id': video_id,
                    'url': video_url,
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'channel': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt']
                })
            
            return videos
            
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error searching YouTube videos: {str(e)}")
            return []
    
    def _check_video_transcript(self, video_url):
        """
        Check if a video has an available transcript
        Returns True if transcript exists, False otherwise
        """
        try:
            transcript = self.youtube_service.get_transcript(video_url)
            return bool(transcript)
        except Exception:
            return False
    
    def process_video(self, video_url, auto_publish=True, categories=None):
        """
        Process a single video to generate and optionally publish an article
        
        Parameters:
        - video_url: YouTube video URL
        - auto_publish: Whether to automatically publish to WordPress
        - categories: List of WordPress category names for the article
        
        Returns:
        - Article data if successful, None otherwise
        """
        try:
            video_id = self.youtube_service.get_video_id(video_url)
            
            # Skip if already processed
            if video_id in self.processed_videos:
                logger.info(f"Video already processed: {video_url}")
                return None
            
            # Get video transcript
            transcript = self.youtube_service.get_transcript(video_url)
            if not transcript:
                logger.warning(f"No transcript available for video: {video_url}")
                return None
            
            # Generate article
            article = self.mistral_service.generate_article(transcript)
            if not article or article.get('status') != 'success':
                logger.error(f"Failed to generate article for video: {video_url}")
                return None
            
            # Publish to WordPress if enabled
            if auto_publish:
                post_id = self.wordpress_service.publish_article(
                    article=article, 
                    video_url=video_url,
                    categories=categories
                )
                
                if post_id:
                    logger.info(f"Article published to WordPress for video: {video_url}")
                else:
                    logger.warning(f"Failed to publish article to WordPress for video: {video_url}")
            
            # Mark as processed
            self.processed_videos.append(video_id)
            self._save_processed_videos()
            
            return article
            
        except Exception as e:
            logger.error(f"Error processing video {video_url}: {str(e)}")
            return None
    
    def run_auto_search(self, queries, max_videos_per_query=1, days_threshold=7, auto_publish=True, categories=None):
        """
        Run automated search for videos based on a list of queries
        
        Parameters:
        - queries: List of search terms
        - max_videos_per_query: Maximum videos to process per query
        - days_threshold: Only consider videos published within this many days
        - auto_publish: Whether to automatically publish to WordPress
        - categories: List of WordPress category names for the articles
        
        Returns:
        - Number of articles successfully generated
        """
        if not queries:
            logger.warning("No search queries provided")
            return 0
        
        # Calculate the date threshold
        published_after = (datetime.utcnow() - timedelta(days=days_threshold)).isoformat() + "Z"
        
        processed_count = 0
        random.shuffle(queries)  # Randomize queries to get diverse content
        
        for query in queries:
            # Skip if we've already processed enough videos
            if processed_count >= max_videos_per_query * len(queries):
                break
                
            logger.info(f"Searching for videos with query: {query}")
            videos = self.search_videos(
                query=query,
                max_results=max_videos_per_query * 3,  # Get more results to account for filtering
                published_after=published_after
            )
            
            # Process videos from this query
            query_processed = 0
            for video in videos:
                # Skip if we've processed enough for this query
                if query_processed >= max_videos_per_query:
                    break
                
                # Process video
                article = self.process_video(
                    video_url=video['url'],
                    auto_publish=auto_publish,
                    categories=categories
                )
                
                if article:
                    query_processed += 1
                    processed_count += 1
                    logger.info(f"Generated article for video: {video['url']}")
                
            logger.info(f"Processed {query_processed} videos for query: {query}")
        
        logger.info(f"Auto-search complete. Generated {processed_count} articles.")
        return processed_count
