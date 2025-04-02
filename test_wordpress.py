#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for WordPress integration
"""

from services.youtube_service import YouTubeService
from services.simple_mistral_service import SimpleMistralService
from services.wordpress_service import WordPressService

def test_wordpress_integration():
    """Test WordPress integration with a single video"""
    print("Starting WordPress integration test...")
    
    # YouTube URL to test
    video_url = input("Enter a YouTube video URL to test: ")
    
    # Initialize services
    youtube_service = YouTubeService()
    mistral_service = SimpleMistralService()
    wordpress_service = WordPressService()
    
    # Check WordPress configuration
    if not wordpress_service.site_url or not wordpress_service.username or not wordpress_service.app_password:
        print("WordPress is not properly configured in .env file!")
        print("Please add WORDPRESS_URL, WORDPRESS_USERNAME, and WORDPRESS_APP_PASSWORD")
        return
    
    print(f"Processing video: {video_url}")
    
    # Get transcript
    try:
        transcript = youtube_service.get_transcript(video_url)
        print(f"Transcript obtained, length: {len(transcript)} characters")
    except Exception as e:
        print(f"Error getting transcript: {str(e)}")
        return
    
    # Generate article
    try:
        print("Generating article with Mistral API (this may take a minute)...")
        article = mistral_service.generate_article(transcript)
        if not article or article.get('status') != 'success':
            print("Failed to generate article!")
            return
        print(f"Article generated successfully, title: {article.get('title')}")
    except Exception as e:
        print(f"Error generating article: {str(e)}")
        return
    
    # Optionally publish to WordPress
    publish = input("Would you like to publish this article to WordPress? (y/n): ").lower().strip()
    if publish == 'y':
        try:
            post_id = wordpress_service.publish_article(
                article=article, 
                video_url=video_url,
                categories=["Test", "YouTube"]
            )
            
            if post_id:
                print(f"Article published successfully to WordPress!")
            else:
                print("Failed to publish article to WordPress!")
        except Exception as e:
            print(f"Error publishing to WordPress: {str(e)}")
    else:
        print("Skipping WordPress publishing")
    
    print("Test completed!")

if __name__ == "__main__":
    test_wordpress_integration()
