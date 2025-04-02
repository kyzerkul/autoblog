#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RSS Monitor for YouTube channels - No API key required
"""

import os
import sys
import time
import json
import logging
import threading
from datetime import datetime
from dotenv import load_dotenv

from services.rss_service import RSSService
from services.wordpress_service import WordPressService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rss_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RSS Monitor")

class RSSMonitor:
    """Monitor for YouTube channel RSS feeds"""
    
    def __init__(self):
        """Initialize the RSS monitor"""
        self.rss_service = RSSService()
        self.wordpress_service = WordPressService()
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Config file for channels
        self.config_file = os.path.join(self.data_dir, 'rss_config.json')
        self.config = self._load_config()
        
        # Initialize monitored channels
        self._start_all_channels()
    
    def _load_config(self):
        """Load RSS monitor configuration"""
        default_config = {
            'monitored_channels': [],
            'auto_publish': True,
            'check_interval': 3600  # Check every hour by default
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
        """Save RSS monitor configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
    
    def _start_all_channels(self):
        """Start monitoring all configured channels"""
        channels = self.config.get('monitored_channels', [])
        if not channels:
            logger.info("No channels configured for monitoring")
            return
        
        auto_publish = self.config.get('auto_publish', True)
        
        for channel_id in channels:
            self.rss_service.start_monitoring(
                channel_id=channel_id,
                auto_publish=auto_publish
            )
            logger.info(f"Started monitoring channel: {channel_id}")
    
    def add_channel(self, channel_id):
        """Add a channel to monitor"""
        if not channel_id or not isinstance(channel_id, str):
            logger.error("Invalid channel ID")
            return False
        
        if channel_id in self.config['monitored_channels']:
            logger.info(f"Channel {channel_id} is already being monitored")
            return False
        
        # Add to config
        self.config['monitored_channels'].append(channel_id)
        self._save_config()
        
        # Start monitoring
        auto_publish = self.config.get('auto_publish', True)
        result = self.rss_service.start_monitoring(
            channel_id=channel_id,
            auto_publish=auto_publish
        )
        
        if result:
            logger.info(f"Started monitoring channel: {channel_id}")
        else:
            logger.warning(f"Failed to start monitoring channel: {channel_id}")
        
        return result
    
    def remove_channel(self, channel_id):
        """Remove a channel from monitoring"""
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
    
    def list_channels(self):
        """List all monitored channels"""
        return self.config['monitored_channels']
    
    def set_auto_publish(self, enabled):
        """Enable or disable auto-publishing to WordPress"""
        self.config['auto_publish'] = bool(enabled)
        self._save_config()
        logger.info(f"Auto-publish set to: {enabled}")
        return True
    
    def set_check_interval(self, interval_seconds):
        """Set the interval for checking RSS feeds (in seconds)"""
        if not isinstance(interval_seconds, int) or interval_seconds < 300:
            logger.warning("Check interval must be at least 300 seconds (5 minutes)")
            return False
        
        self.config['check_interval'] = interval_seconds
        self._save_config()
        logger.info(f"Check interval set to: {interval_seconds} seconds")
        return True
    
    def run_interactive(self):
        """Run the monitor in interactive mode"""
        print("\n=== YouTube Channel RSS Monitor ===")
        print("This program will monitor YouTube channels and generate articles")
        print("from new videos as they are published.")
        
        while True:
            print("\nOptions:")
            print("1. Add a YouTube channel to monitor")
            print("2. Remove a channel from monitoring")
            print("3. List all monitored channels")
            print("4. Change auto-publish setting")
            print("5. Change check interval")
            print("6. Exit")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                channel_id = input("Enter the YouTube channel ID: ").strip()
                if self.add_channel(channel_id):
                    print(f"Channel {channel_id} added successfully!")
                else:
                    print("Failed to add channel. Check the logs for details.")
            
            elif choice == '2':
                channels = self.list_channels()
                if not channels:
                    print("No channels are currently being monitored.")
                    continue
                
                print("\nCurrently monitored channels:")
                for i, channel in enumerate(channels, 1):
                    print(f"{i}. {channel}")
                
                idx = input("\nEnter the number of the channel to remove: ").strip()
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(channels):
                        channel_id = channels[idx]
                        if self.remove_channel(channel_id):
                            print(f"Channel {channel_id} removed successfully!")
                        else:
                            print("Failed to remove channel. Check the logs for details.")
                    else:
                        print("Invalid channel number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            elif choice == '3':
                channels = self.list_channels()
                if not channels:
                    print("No channels are currently being monitored.")
                else:
                    print("\nCurrently monitored channels:")
                    for i, channel in enumerate(channels, 1):
                        print(f"{i}. {channel}")
            
            elif choice == '4':
                current = self.config.get('auto_publish', True)
                print(f"Auto-publish is currently: {'enabled' if current else 'disabled'}")
                new_setting = input("Enable auto-publish? (y/n): ").strip().lower()
                if new_setting in ('y', 'yes'):
                    self.set_auto_publish(True)
                    print("Auto-publish enabled!")
                elif new_setting in ('n', 'no'):
                    self.set_auto_publish(False)
                    print("Auto-publish disabled!")
                else:
                    print("Invalid input. No changes made.")
            
            elif choice == '5':
                current = self.config.get('check_interval', 3600)
                print(f"Current check interval: {current} seconds")
                try:
                    new_interval = int(input("Enter new interval in seconds (minimum 300): ").strip())
                    if self.set_check_interval(new_interval):
                        print(f"Check interval updated to {new_interval} seconds!")
                    else:
                        print("Failed to update interval. Minimum is 300 seconds.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            elif choice == '6':
                print("Exiting...")
                # The monitoring will continue in background threads
                print("Note: Channel monitoring continues in the background.")
                print("Restart this program to manage channels later.")
                break
            
            else:
                print("Invalid choice. Please try again.")
    
    def run(self):
        """Run the monitor in background mode"""
        if not self.config['monitored_channels']:
            logger.warning("No channels configured for monitoring. Use interactive mode to add channels.")
            return
        
        logger.info("RSS Monitor started")
        logger.info(f"Monitoring {len(self.config['monitored_channels'])} channels")
        logger.info(f"Auto-publish: {'enabled' if self.config.get('auto_publish', True) else 'disabled'}")
        
        # The monitoring runs in separate threads managed by RSSService
        # This is just to keep the main thread alive
        try:
            while True:
                time.sleep(60)  # Just keep the main thread alive
        except KeyboardInterrupt:
            logger.info("RSS Monitor stopped by user")


class RSSService:
    def __init__(self):
        pass

    def get_channel_feed_url(self, channel_id_or_url):
        """Generates the RSS feed URL for a YouTube channel"""
        # If it's already a feed URL, return it directly
        if channel_id_or_url.startswith('http') and 'feeds/videos.xml' in channel_id_or_url:
            return channel_id_or_url
        
        # If it's a channel ID (starting with UC), convert to feed URL
        if channel_id_or_url.startswith('UC'):
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id_or_url}"
            
        # If it's possibly a username
        if not channel_id_or_url.startswith('http'):
            return f"https://www.youtube.com/feeds/videos.xml?user={channel_id_or_url}"
        
        # If it's a channel URL, try to extract the ID
        import re
        channel_match = re.search(r'youtube\.com/channel/(UC[\w-]+)', channel_id_or_url)
        if channel_match:
            channel_id = channel_match.group(1)
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            
        # If it's a user URL
        user_match = re.search(r'youtube\.com/user/([\w-]+)', channel_id_or_url)
        if user_match:
            username = user_match.group(1)
            return f"https://www.youtube.com/feeds/videos.xml?user={username}"
            
        # If it's a custom URL
        custom_match = re.search(r'youtube\.com/c/([\w-]+)', channel_id_or_url)
        if custom_match:
            custom_name = custom_match.group(1)
            return f"https://www.youtube.com/feeds/videos.xml?user={custom_name}"
            
        # Default to the original input if we can't parse it
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id_or_url}"


def get_channel_id_from_url(url):
    """Extract channel ID from various YouTube URL formats"""
    import re
    
    # Pattern for channel URLs like: https://www.youtube.com/channel/UC...
    channel_pattern = re.compile(r'youtube\.com/channel/(UC[\w-]+)')
    match = channel_pattern.search(url)
    if match:
        return match.group(1)
    
    # For user URLs like: https://www.youtube.com/user/username
    # or custom URLs like: https://www.youtube.com/c/customname
    # We need to fetch the page and extract the channel ID, which requires additional libraries
    print("Could not extract channel ID from URL.")
    print("Please provide the channel ID directly (starts with 'UC').")
    print("You can find it in the URL when you visit the channel page:")
    print("https://www.youtube.com/channel/UCXXXXXXXXXXXXXXXXXXXXXXXX")
    
    return None


if __name__ == "__main__":
    import sys
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        # If channel ID or URL provided, add it and run in background
        channel_arg = sys.argv[1]
        
        # Check if it looks like a URL
        if '/' in channel_arg:
            channel_id = get_channel_id_from_url(channel_arg)
            if not channel_id:
                print("Please run again with a valid channel ID.")
                sys.exit(1)
        else:
            # Assume it's a channel ID
            channel_id = channel_arg
        
        monitor = RSSMonitor()
        if monitor.add_channel(channel_id):
            print(f"Channel {channel_id} added successfully!")
            print("Running in background mode. Press Ctrl+C to exit.")
            monitor.run()
        else:
            print("Failed to add channel. Check the logs for details.")
    else:
        # No arguments, run in interactive mode
        monitor = RSSMonitor()
        monitor.run_interactive()
