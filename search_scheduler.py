#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube Search Scheduler - Without API Key
Uses web scraping to search for YouTube videos and generate articles
"""

import os
import sys
import time
import json
import random
import logging
import schedule
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

from services.scraper_service import ScraperService
from services.youtube_service import YouTubeService
from services.simple_mistral_service import SimpleMistralService
from services.wordpress_service import WordPressService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("search_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Search Scheduler")

class SearchScheduler:
    """Scheduler for automatic YouTube video search and article generation"""
    
    def __init__(self):
        """Initialize the search scheduler"""
        self.scraper_service = ScraperService()
        self.youtube_service = YouTubeService()
        self.mistral_service = SimpleMistralService()
        self.wordpress_service = WordPressService()
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Config file for search queries
        self.config_file = os.path.join(self.data_dir, 'search_config.json')
        self.processed_file = os.path.join(self.data_dir, 'processed_videos.json')
        self.config = self._load_config()
        self.processed_videos = self._load_processed_videos()
    
    def _load_config(self):
        """Load search configuration"""
        default_config = {
            'search_queries': [
                "artificial intelligence tutorial",
                "machine learning explained",
                "python programming tips",
                "web development best practices",
                "data science for beginners"
            ],
            'daily_search_times': ["08:00", "12:00", "16:00", "20:00"],
            'videos_per_search': 1,
            'days_threshold': 7,  # Only videos published in last 7 days
            'auto_publish': True,
            'categories': ["Technology", "Tutorials"],
            'trending_searches': True  # Whether to include trending videos
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create default config file
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return default_config
    
    def _save_config(self):
        """Save search configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
    
    def _load_processed_videos(self):
        """Load the list of already processed videos"""
        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return []
        except Exception as e:
            logger.error(f"Error loading processed videos: {str(e)}")
            return []
    
    def _save_processed_videos(self):
        """Save the list of processed videos"""
        try:
            with open(self.processed_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_videos, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed videos: {str(e)}")
    
    def is_video_processed(self, video_id):
        """Check if a video has already been processed"""
        return video_id in self.processed_videos
    
    def mark_video_processed(self, video_id):
        """Mark a video as processed"""
        if video_id not in self.processed_videos:
            self.processed_videos.append(video_id)
            self._save_processed_videos()
    
    def add_search_query(self, query):
        """Add a search query to the configuration"""
        if not query or not isinstance(query, str):
            return False
        
        if query not in self.config['search_queries']:
            self.config['search_queries'].append(query)
            self._save_config()
            logger.info(f"Added search query: {query}")
            return True
        
        return False
    
    def remove_search_query(self, query):
        """Remove a search query from the configuration"""
        if query in self.config['search_queries']:
            self.config['search_queries'].remove(query)
            self._save_config()
            logger.info(f"Removed search query: {query}")
            return True
        
        return False
    
    def set_search_times(self, times):
        """Set daily search times"""
        if not times or not isinstance(times, list):
            return False
        
        # Validate time format (HH:MM)
        import re
        for time_str in times:
            if not re.match(r'^\d{2}:\d{2}$', time_str):
                logger.warning(f"Invalid time format: {time_str}. Expected format: HH:MM")
                return False
        
        self.config['daily_search_times'] = times
        self._save_config()
        
        # Reset the scheduler
        self._setup_schedule()
        
        logger.info(f"Updated search times: {times}")
        return True
    
    def set_videos_per_search(self, count):
        """Set number of videos to process per search query"""
        if not isinstance(count, int) or count < 1:
            return False
        
        self.config['videos_per_search'] = count
        self._save_config()
        logger.info(f"Videos per search set to: {count}")
        return True
    
    def set_days_threshold(self, days):
        """Set the number of days to look back for videos"""
        if not isinstance(days, int) or days < 1:
            return False
        
        self.config['days_threshold'] = days
        self._save_config()
        logger.info(f"Days threshold set to: {days}")
        return True
    
    def process_video(self, video_url, categories=None):
        """Process a single video to generate and publish an article"""
        try:
            video_id = video_url.split('v=')[-1].split('&')[0]
            
            # Skip if already processed
            if self.is_video_processed(video_id):
                logger.info(f"Video {video_id} already processed, skipping")
                return False
            
            # Get transcript
            logger.info(f"Getting transcript for video: {video_url}")
            transcript = self.youtube_service.get_transcript(video_url)
            
            if not transcript:
                logger.warning(f"No transcript available for video: {video_url}")
                self.mark_video_processed(video_id)  # Mark as processed to avoid retrying
                return False
            
            # Generate article
            logger.info(f"Generating article for video: {video_url}")
            article = self.mistral_service.generate_article(transcript)
            
            if not article or article.get('status') != 'success':
                logger.warning(f"Failed to generate article for video: {video_url}")
                return False
            
            # Publish to WordPress if auto-publish is enabled
            if self.config.get('auto_publish', True):
                categories = categories or self.config.get('categories', [])
                
                logger.info(f"Publishing article to WordPress: {article.get('title')}")
                post_id = self.wordpress_service.publish_article(
                    article=article,
                    video_url=video_url,
                    categories=categories
                )
                
                if post_id:
                    logger.info(f"Article published successfully, post ID: {post_id}")
                else:
                    logger.warning(f"Failed to publish article for video: {video_url}")
                    return False
            
            # Mark as processed
            self.mark_video_processed(video_id)
            return True
            
        except Exception as e:
            logger.error(f"Error processing video {video_url}: {str(e)}")
            return False
    
    def run_search_task(self):
        """Run the search task to find and process videos"""
        try:
            logger.info("Running scheduled YouTube search task")
            
            # Get configuration
            queries = self.config.get('search_queries', [])
            max_videos = self.config.get('videos_per_search', 1)
            days_threshold = self.config.get('days_threshold', 7)
            include_trending = self.config.get('trending_searches', True)
            
            if not queries and not include_trending:
                logger.warning("No search queries configured and trending videos disabled")
                return 0
            
            published_after = datetime.now() - timedelta(days=days_threshold)
            processed_count = 0
            
            # Process trending videos if enabled
            if include_trending:
                logger.info("Searching for trending videos")
                trending_videos = self.scraper_service.get_trending_videos(max_results=max_videos)
                
                for video in trending_videos:
                    try:
                        video_url = video['url']
                        video_id = video['id']
                        
                        if not self.is_video_processed(video_id):
                            logger.info(f"Processing trending video: {video['title']}")
                            if self.process_video(video_url, categories=['Trending']):
                                processed_count += 1
                                
                                # Add some delay to avoid rate limiting
                                time.sleep(random.uniform(5, 10))
                    except Exception as e:
                        logger.error(f"Error processing trending video: {str(e)}")
            
            # Process videos from search queries
            for query in queries:
                try:
                    logger.info(f"Searching for videos with query: {query}")
                    search_results = self.scraper_service.search_videos(
                        query=query,
                        max_results=max_videos * 3,  # Get more results to allow for filtering
                        published_after=published_after
                    )
                    
                    query_processed = 0
                    for video in search_results:
                        try:
                            video_url = video['url']
                            video_id = video['id']
                            
                            if not self.is_video_processed(video_id):
                                logger.info(f"Processing video from search: {video['title']}")
                                if self.process_video(video_url):
                                    processed_count += 1
                                    query_processed += 1
                                    
                                    # Add some delay to avoid rate limiting
                                    time.sleep(random.uniform(5, 10))
                                    
                                    # Break if we've processed enough videos for this query
                                    if query_processed >= max_videos:
                                        break
                        except Exception as e:
                            logger.error(f"Error processing search result: {str(e)}")
                            
                except Exception as e:
                    logger.error(f"Error searching for query '{query}': {str(e)}")
            
            logger.info(f"Search task completed. Generated {processed_count} articles")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error running search task: {str(e)}")
            return 0
    
    def _setup_schedule(self):
        """Setup the schedule based on configuration"""
        # Clear existing schedule
        schedule.clear()
        
        # Setup daily search tasks
        for time_str in self.config.get('daily_search_times', []):
            schedule.every().day.at(time_str).do(self.run_search_task)
            logger.info(f"Scheduled daily search at {time_str}")
    
    def run_interactive(self):
        """Run the scheduler in interactive mode"""
        print("\n=== YouTube Search Scheduler (No API Key) ===")
        print("This program will search for YouTube videos and generate articles")
        print("based on configured search queries and schedules.")
        
        while True:
            print("\nOptions:")
            print("1. Run search task now")
            print("2. Add a search query")
            print("3. Remove a search query")
            print("4. List all search queries")
            print("5. Change search times")
            print("6. Change videos per search")
            print("7. Change days threshold")
            print("8. Toggle trending searches")
            print("9. Toggle auto-publish")
            print("10. Exit")
            
            choice = input("\nEnter your choice (1-10): ").strip()
            
            if choice == '1':
                print("Running search task...")
                count = self.run_search_task()
                print(f"Search task completed. Generated {count} articles.")
            
            elif choice == '2':
                query = input("Enter a search query: ").strip()
                if self.add_search_query(query):
                    print(f"Search query '{query}' added successfully!")
                else:
                    print("Failed to add query. It may already exist.")
            
            elif choice == '3':
                queries = self.config.get('search_queries', [])
                if not queries:
                    print("No search queries configured.")
                    continue
                
                print("\nCurrent search queries:")
                for i, query in enumerate(queries, 1):
                    print(f"{i}. {query}")
                
                idx = input("\nEnter the number of the query to remove: ").strip()
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(queries):
                        query = queries[idx]
                        if self.remove_search_query(query):
                            print(f"Search query '{query}' removed successfully!")
                        else:
                            print("Failed to remove query.")
                    else:
                        print("Invalid query number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            elif choice == '4':
                queries = self.config.get('search_queries', [])
                if not queries:
                    print("No search queries configured.")
                else:
                    print("\nCurrent search queries:")
                    for i, query in enumerate(queries, 1):
                        print(f"{i}. {query}")
            
            elif choice == '5':
                current = self.config.get('daily_search_times', [])
                print(f"Current search times: {', '.join(current)}")
                
                times_str = input("Enter new search times (comma-separated, format HH:MM): ").strip()
                times = [t.strip() for t in times_str.split(',') if t.strip()]
                
                if self.set_search_times(times):
                    print(f"Search times updated to: {', '.join(times)}")
                else:
                    print("Failed to update search times. Check the format (HH:MM).")
            
            elif choice == '6':
                current = self.config.get('videos_per_search', 1)
                print(f"Current videos per search: {current}")
                
                try:
                    new_count = int(input("Enter new count: ").strip())
                    if self.set_videos_per_search(new_count):
                        print(f"Videos per search updated to: {new_count}")
                    else:
                        print("Failed to update count. It must be a positive integer.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            elif choice == '7':
                current = self.config.get('days_threshold', 7)
                print(f"Current days threshold: {current}")
                
                try:
                    new_days = int(input("Enter new threshold (days): ").strip())
                    if self.set_days_threshold(new_days):
                        print(f"Days threshold updated to: {new_days}")
                    else:
                        print("Failed to update threshold. It must be a positive integer.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            elif choice == '8':
                current = self.config.get('trending_searches', True)
                print(f"Trending searches are currently: {'enabled' if current else 'disabled'}")
                
                new_setting = input("Enable trending searches? (y/n): ").strip().lower()
                if new_setting in ('y', 'yes'):
                    self.config['trending_searches'] = True
                    self._save_config()
                    print("Trending searches enabled!")
                elif new_setting in ('n', 'no'):
                    self.config['trending_searches'] = False
                    self._save_config()
                    print("Trending searches disabled!")
                else:
                    print("Invalid input. No changes made.")
            
            elif choice == '9':
                current = self.config.get('auto_publish', True)
                print(f"Auto-publish is currently: {'enabled' if current else 'disabled'}")
                
                new_setting = input("Enable auto-publish? (y/n): ").strip().lower()
                if new_setting in ('y', 'yes'):
                    self.config['auto_publish'] = True
                    self._save_config()
                    print("Auto-publish enabled!")
                elif new_setting in ('n', 'no'):
                    self.config['auto_publish'] = False
                    self._save_config()
                    print("Auto-publish disabled!")
                else:
                    print("Invalid input. No changes made.")
            
            elif choice == '10':
                print("Exiting...")
                break
            
            else:
                print("Invalid choice. Please try again.")
    
    def run(self):
        """Run the scheduler in background mode"""
        self._setup_schedule()
        
        logger.info("Search Scheduler started")
        logger.info(f"Configured with {len(self.config['search_queries'])} search queries")
        logger.info(f"Scheduled searches at: {', '.join(self.config['daily_search_times'])}")
        
        # Run initial search task
        self.run_search_task()
        
        # Run the scheduler loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(300)  # Wait 5 minutes in case of error


if __name__ == "__main__":
    import sys
    
    scheduler = SearchScheduler()
    
    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1] == 'run-once':
        # Run search task once and exit
        print("Running search task once...")
        count = scheduler.run_search_task()
        print(f"Search task completed. Generated {count} articles.")
    else:
        # Run in interactive mode
        scheduler.run_interactive()
