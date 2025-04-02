#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automated scheduler for YouTube article generation
"""

import os
import sys
import time
import json
import random
import logging
import schedule
import threading
from datetime import datetime
from dotenv import load_dotenv

from services.rss_service import RSSService
from services.youtube_search_service import YouTubeSearchService
from services.simple_mistral_service import SimpleMistralService
from services.wordpress_service import WordPressService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Auto Scheduler")

class AutoScheduler:
    """Scheduler for automatic YouTube article generation"""
    
    def __init__(self):
        """Initialize the scheduler"""
        self.rss_service = RSSService()
        self.search_service = YouTubeSearchService()
        self.wordpress_service = WordPressService()
        self.simple_mistral_service = SimpleMistralService()
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Config file for channels and search queries
        self.config_file = os.path.join(self.data_dir, 'scheduler_config.json')
        self.config = self._load_config()
        
        # Initialize monitored channels
        for channel_id in self.config.get('monitored_channels', []):
            self.start_channel_monitoring(channel_id)
    
    def _load_config(self):
        """Load scheduler configuration"""
        default_config = {
            'monitored_channels': [],
            'search_queries': [
                "artificial intelligence tutorial",
                "machine learning explained",
                "python programming tips",
                "web development best practices",
                "data science for beginners"
            ],
            'daily_search_times': ["08:00", "12:00", "16:00", "20:00"],
            'videos_per_search': 1,
            'auto_publish': True,
            'categories': ["Technology", "Tutorials"]
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
        """Save scheduler configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
    
    def start_channel_monitoring(self, channel_id):
        """Start monitoring a YouTube channel"""
        if channel_id in self.config['monitored_channels']:
            logger.info(f"Channel {channel_id} is already being monitored")
            return False
        
        # Add to config
        self.config['monitored_channels'].append(channel_id)
        self._save_config()
        
        # Start monitoring
        result = self.rss_service.start_monitoring(
            channel_id=channel_id,
            auto_publish=self.config.get('auto_publish', True)
        )
        
        if result:
            logger.info(f"Started monitoring channel: {channel_id}")
        else:
            logger.warning(f"Failed to start monitoring channel: {channel_id}")
        
        return result
    
    def stop_channel_monitoring(self, channel_id):
        """Stop monitoring a YouTube channel"""
        if channel_id not in self.config['monitored_channels']:
            logger.info(f"Channel {channel_id} is not being monitored")
            return False
        
        # Remove from config
        self.config['monitored_channels'].remove(channel_id)
        self._save_config()
        
        # Stop monitoring
        result = self.rss_service.stop_monitoring(channel_id)
        
        if result:
            logger.info(f"Stopped monitoring channel: {channel_id}")
        else:
            logger.warning(f"Failed to stop monitoring channel: {channel_id}")
        
        return result
    
    def run_search_task(self):
        """Run automated search for YouTube videos"""
        try:
            logger.info("Running scheduled YouTube search task")
            
            # Get configuration
            queries = self.config.get('search_queries', [])
            max_videos = self.config.get('videos_per_search', 1)
            auto_publish = self.config.get('auto_publish', True)
            categories = self.config.get('categories', [])
            
            if not queries:
                logger.warning("No search queries configured")
                return
            
            # Run the search
            processed_count = self.search_service.run_auto_search(
                queries=queries,
                max_videos_per_query=max_videos,
                days_threshold=7,
                auto_publish=auto_publish,
                categories=categories
            )
            
            logger.info(f"Search task completed. Generated {processed_count} articles")
            
        except Exception as e:
            logger.error(f"Error running search task: {str(e)}")
    
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
    
    def _setup_schedule(self):
        """Setup the schedule based on configuration"""
        # Clear existing schedule
        schedule.clear()
        
        # Setup daily search tasks
        for time_str in self.config.get('daily_search_times', []):
            schedule.every().day.at(time_str).do(self.run_search_task)
            logger.info(f"Scheduled daily search at {time_str}")
        
        # Add additional maintenance tasks if needed
        # For example, cleanup old data every day at midnight
        schedule.every().day.at("00:00").do(self._maintenance_task)
    
    def _maintenance_task(self):
        """Run maintenance tasks"""
        logger.info("Running daily maintenance tasks")
        # Add any cleanup or maintenance operations here
        # For example, removing old logs, etc.
    
    def run(self):
        """Run the scheduler"""
        self._setup_schedule()
        
        logger.info("Auto Scheduler started")
        logger.info(f"Monitoring {len(self.config['monitored_channels'])} channels")
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
    import re
    scheduler = AutoScheduler()
    scheduler.run()
