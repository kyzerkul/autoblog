import feedparser
import threading
import time
from datetime import datetime, timedelta
from .youtube_service import YouTubeService
from .simple_mistral_service import SimpleMistralService
from .wordpress_service import WordPressService
from .supabase_service import SupabaseService
import os
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rss_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RSS Service")

class RSSService:
    def __init__(self, wordpress_service=None, project_id=None):
        self.youtube_service = YouTubeService()
        self.mistral_service = SimpleMistralService()
        self.wordpress_service = wordpress_service or WordPressService()
        self.supabase = SupabaseService()
        self.project_id = project_id
        self.monitoring_threads = {}
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # History file for processed videos
        self.history_file = os.path.join(self.data_dir, 'processed_videos.json')
        
        # Load processed videos after initializing history_file
        self.processed_videos = self._load_processed_videos()
        
    def _load_processed_videos(self):
        """Load the list of processed videos from storage"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            logger.error(f"Error loading processed videos: {str(e)}")
            return set()
    
    def _save_processed_videos(self):
        """Save the list of processed videos to storage"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_videos), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed videos: {str(e)}")

    def get_channel_feed_url(self, channel_id):
        """Generates the RSS feed URL for a YouTube channel"""
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    def process_video(self, video_url, channel_id=None, channel_name=None, auto_publish=True, project_id=None):
        """Processes an individual video"""
        try:
            # Use project_id from params or instance
            current_project_id = project_id or self.project_id
            
            # Extract video ID
            video_id = self.youtube_service.get_video_id(video_url)
            
            # Check if the video has already been processed
            if video_id in self.processed_videos:
                logger.info(f"Video already processed: {video_url}")
                return None

            # Extract transcript
            transcript = self.youtube_service.get_transcript(video_url)
            if not transcript:
                logger.warning(f"No transcript available for video: {video_url}")
                return None
            
            # Generate article
            article = self.mistral_service.generate_article(transcript)
            if not article or article.get('status') != 'success':
                logger.error(f"Failed to generate article for video: {video_url}")
                return None
            
            post_id = None
            
            # Publish to WordPress if enabled
            if auto_publish:
                # Prepare categories - use channel name if available
                categories = []
                if channel_name:
                    categories.append(channel_name)
                    categories.append("YouTube")
                
                post_id = self.wordpress_service.publish_article(
                    article=article, 
                    video_url=video_url,
                    categories=categories
                )
                
                if post_id:
                    logger.info(f"Article published to WordPress for video: {video_url}")
                    
                    # Save article to Supabase if we have a project ID
                    if current_project_id:
                        try:
                            # Prepare article data for Supabase
                            article_data = {
                                "project_id": current_project_id,
                                "video_id": video_id,
                                "video_url": video_url,
                                "wordpress_post_id": str(post_id),
                                "title": article.get('title', 'Generated Article'),
                                "published_at": datetime.now().isoformat(),
                                "status": "published"
                            }
                            
                            # Insert into Supabase
                            result = self.supabase.client.table("published_articles").insert(article_data).execute()
                            
                            if result.data and len(result.data) > 0:
                                logger.info(f"Article saved to Supabase for video: {video_url}")
                            else:
                                logger.warning(f"Failed to save article to Supabase for video: {video_url}")
                        except Exception as e:
                            logger.error(f"Error saving article to Supabase: {str(e)}")
                else:
                    logger.warning(f"Failed to publish article to WordPress for video: {video_url}")
            
            # Save the article locally as well
            file_path = self._save_article(article, video_url)
            
            # Mark the video as processed
            self.processed_videos.add(video_id)
            self._save_processed_videos()
            
            return article
            
        except Exception as e:
            logger.error(f"Error processing video {video_url}: {str(e)}")
            return None

    def _save_article(self, article, video_url):
        """Saves the generated article"""
        try:
            # Check that the article was successfully generated
            if not article or 'status' not in article or article['status'] != 'success':
                logger.error(f"Unable to save article for {video_url}: article not generated or in error")
                return None
            
            # Create articles folder if it doesn't exist
            articles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'articles')
            if not os.path.exists(articles_dir):
                os.makedirs(articles_dir)
            
            # Extract video ID from URL
            video_id = self.youtube_service.get_video_id(video_url)
            
            # Create a filename based on video ID and date
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{video_id}_{timestamp}.html"
            filepath = os.path.join(articles_dir, filename)
            
            # Create a complete HTML document
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article.get('title', 'Generated Article')}</title>
    <meta name="description" content="{article.get('meta_description', '')}">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #444; margin-top: 30px; }}
        h3 {{ color: #555; }}
        p {{ margin-bottom: 16px; }}
        .source {{ font-style: italic; color: #777; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>{article.get('title', 'Generated Article')}</h1>
    {article.get('content', '')}
    <div class="source">Source: <a href="{video_url}" target="_blank">{video_url}</a></div>
</body>
</html>"""
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Article saved successfully: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving article for {video_url}: {str(e)}")
            return None

    def monitor_channel(self, channel_id, auto_publish=True):
        """Monitors a YouTube channel for new videos"""
        try:
            # Store the monitoring state for this thread to check later
            thread_id = f"{channel_id}_{int(time.time())}"
            self.monitoring_threads[channel_id] = {
                "thread_id": thread_id,
                "active": True,
                "last_check": datetime.now()
            }
            
            # Get the channel feed once to extract channel name
            feed_url = self.get_channel_feed_url(channel_id)
            feed = feedparser.parse(feed_url)
            
            # Extract channel name if available
            channel_name = None
            if feed and hasattr(feed, 'feed') and hasattr(feed.feed, 'title'):
                channel_name = feed.feed.title
                logger.info(f"Monitoring channel: {channel_name} ({channel_id})")
            else:
                logger.info(f"Monitoring channel ID: {channel_id}")
            
            # Process immediately all videos from the last 48 hours
            logger.info("Processing recent videos immediately...")
            recent_count = self._process_recent_videos(feed, channel_id, channel_name, auto_publish, hours=48)
            logger.info(f"Processed {recent_count} recent videos")
            
            # Store the last check time
            last_check_time = datetime.now()
            
            # Start continuous monitoring
            logger.info(f"Starting continuous monitoring for channel: {channel_id}")
            while self.monitoring_threads.get(channel_id, {}).get("active", False):
                try:
                    # Update last check time in monitoring data
                    if channel_id in self.monitoring_threads:
                        self.monitoring_threads[channel_id]["last_check"] = datetime.now()
                    
                    # Parse the feed
                    feed = feedparser.parse(feed_url)
                    
                    # Process each entry (video)
                    processed_count = 0
                    for entry in feed.entries:
                        video_url = entry.link
                        
                        # Skip if already processed
                        video_id = self.youtube_service.get_video_id(video_url)
                        if video_id in self.processed_videos:
                            continue
                        
                        # Extract published date
                        published = None
                        if hasattr(entry, 'published_parsed'):
                            published = datetime(*entry.published_parsed[:6])
                        
                        # Skip old videos (older than the last check)
                        if published and published < last_check_time:
                            continue
                            
                        # Process the video
                        logger.info(f"Processing new video: {video_url}")
                        result = self.process_video(video_url, channel_id, channel_name, auto_publish)
                        
                        if result:
                            processed_count += 1
                            logger.info(f"Successfully generated article for video: {video_url}")
                    
                    # Update the last check time
                    last_check_time = datetime.now()
                    
                    if processed_count > 0:
                        logger.info(f"Processed {processed_count} new videos from channel {channel_id}")
                    
                    # Wait before next check (every 30 minutes - more frequent)
                    logger.info(f"Waiting 30 minutes before next check for channel {channel_id}")
                    time.sleep(1800)
                    
                except Exception as e:
                    logger.error(f"Error during channel monitoring iteration: {str(e)}")
                    logger.info("Waiting 5 minutes before retry")
                    time.sleep(300)  # Wait 5 minutes in case of error
                    
        except Exception as e:
            logger.error(f"Error monitoring channel {channel_id}: {str(e)}")
    
    def _process_recent_videos(self, feed, channel_id, channel_name, auto_publish, hours=48):
        """Process recent videos from the feed"""
        if not feed or not hasattr(feed, 'entries'):
            return 0
            
        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(hours=hours)
        processed_count = 0
        
        # Sort entries by published date (newest first)
        sorted_entries = []
        for entry in feed.entries:
            published = None
            if hasattr(entry, 'published_parsed'):
                published = datetime(*entry.published_parsed[:6])
                sorted_entries.append((entry, published))
        
        # Sort by date, newest first
        sorted_entries.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
        
        # Process recent videos
        for entry, published in sorted_entries:
            # Skip if too old
            if published and published < cutoff_time:
                continue
                
            video_url = entry.link
            video_id = self.youtube_service.get_video_id(video_url)
            
            # Skip if already processed
            if video_id in self.processed_videos:
                logger.info(f"Skipping already processed video: {video_url}")
                continue
                
            # Process the video
            logger.info(f"Processing recent video: {video_url}")
            print(f"Processing recent video: {video_url}")  # Console output for debugging
            result = self.process_video(
                video_url, 
                channel_id=channel_id, 
                channel_name=channel_name, 
                auto_publish=auto_publish
            )
            
            if result:
                processed_count += 1
                logger.info(f"Successfully generated article for video: {video_url}")
                print(f"Successfully generated article for video: {video_url}")
                # Use English text for YouTube video link
                if auto_publish:
                    print(f"Article published to WordPress as draft")
                else:
                    print(f"Article saved locally (not published to WordPress)")
            else:
                print(f"Failed to process video: {video_url}")
        
        return processed_count

    def start_monitoring(self, channel_id, auto_publish=True):
        """Starts monitoring a YouTube channel in a separate thread"""
        if channel_id in self.monitoring_threads and self.monitoring_threads[channel_id].get("active", False):
            logger.info(f"Already monitoring channel {channel_id}")
            return False

        thread = threading.Thread(
            target=self.monitor_channel,
            args=(channel_id, auto_publish),
            daemon=True
        )
        thread.start()
        
        # Store thread object for reference
        if channel_id in self.monitoring_threads:
            self.monitoring_threads[channel_id]["thread"] = thread
            
        logger.info(f"Started monitoring channel {channel_id}")
        return True
        
    def stop_monitoring(self, channel_id):
        """
        Stops monitoring a channel
        Note: This can't directly stop the thread, but marks it so it will exit on next iteration
        """
        if channel_id in self.monitoring_threads:
            # Mark the thread as inactive so it will exit on next loop iteration
            self.monitoring_threads[channel_id]["active"] = False
            logger.info(f"Stopped monitoring channel {channel_id}")
            return True
        else:
            logger.info(f"Channel {channel_id} is not being monitored")
            return False
            
    def get_monitoring_thread(self, channel_id):
        """Gets the monitoring thread for a channel if it exists"""
        if channel_id in self.monitoring_threads:
            return self.monitoring_threads[channel_id].get("thread")
        return None
        
    def is_monitoring(self, channel_id):
        """Checks if a channel is being monitored"""
        return channel_id in self.monitoring_threads and self.monitoring_threads[channel_id].get("active", False)
        
    def get_monitored_channels(self):
        """Returns a list of channels currently being monitored"""
        return list(self.monitoring_threads.keys())