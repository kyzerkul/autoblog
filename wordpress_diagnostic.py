#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WordPress Connection Diagnostic Tool
"""

import os
import sys
import requests
from dotenv import load_dotenv
import json

# Force reload of environment variables
load_dotenv(override=True)

def check_env_vars():
    """Check if WordPress environment variables are set"""
    wordpress_url = os.getenv("WORDPRESS_URL")
    wordpress_username = os.getenv("WORDPRESS_USERNAME")
    wordpress_password = os.getenv("WORDPRESS_APP_PASSWORD")
    
    print("WordPress Environment Variables Check:")
    print(f"WORDPRESS_URL: {'✓ Set to: ' + wordpress_url if wordpress_url else '✗ Not set'}")
    print(f"WORDPRESS_USERNAME: {'✓ Set to: ' + wordpress_username if wordpress_username else '✗ Not set'}")
    print(f"WORDPRESS_APP_PASSWORD: {'✓ Set' if wordpress_password else '✗ Not set'}")
    
    return wordpress_url, wordpress_username, wordpress_password

def test_connection(url, username, password):
    """Test connection to WordPress API"""
    if not (url and username and password):
        print("\nCannot test connection: Missing credentials")
        return False
    
    # Ensure URL ends without trailing slash
    url = url.rstrip('/')
    
    try:
        # Test basic connection to the site
        print(f"\nTesting connection to {url}...")
        site_response = requests.get(url, timeout=10)
        print(f"Site connection: {'✓ Success' if site_response.status_code == 200 else f'✗ Failed ({site_response.status_code})'}")
        
        # Test WordPress API
        api_url = f"{url}/wp-json"
        print(f"Testing WordPress API at {api_url}...")
        api_response = requests.get(api_url, timeout=10)
        
        if api_response.status_code == 200:
            print("WordPress API: ✓ API available")
            try:
                api_data = api_response.json()
                print(f"WordPress version: {api_data.get('version', 'Unknown')}")
            except:
                print("Warning: Could not parse API response as JSON")
        else:
            print(f"WordPress API: ✗ API not available (Status code: {api_response.status_code})")
            return False
        
        # Test authentication
        auth_url = f"{url}/wp-json/wp/v2/users/me"
        print(f"\nTesting authentication at {auth_url}...")
        
        auth_response = requests.get(
            auth_url,
            auth=(username, password),
            timeout=10
        )
        
        if auth_response.status_code == 200:
            print("Authentication: ✓ Success")
            user_data = auth_response.json()
            print(f"Logged in as: {user_data.get('name', 'Unknown')} (ID: {user_data.get('id', 'Unknown')})")
            return True
        else:
            print(f"Authentication: ✗ Failed (Status code: {auth_response.status_code})")
            print(f"Response: {auth_response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectTimeout:
        print(f"✗ Connection timeout to {url}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Connection error: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def check_posts(url, username, password):
    """Check if we can list posts from the WordPress site"""
    if not (url and username and password):
        return False
    
    url = url.rstrip('/')
    posts_url = f"{url}/wp-json/wp/v2/posts"
    
    try:
        print(f"\nFetching posts from {posts_url}...")
        response = requests.get(
            posts_url,
            auth=(username, password),
            params={"per_page": 3},
            timeout=10
        )
        
        if response.status_code == 200:
            posts = response.json()
            print(f"Successfully retrieved {len(posts)} posts")
            for post in posts:
                print(f"- {post.get('title', {}).get('rendered', 'Untitled')} (ID: {post.get('id', 'Unknown')})")
            return True
        else:
            print(f"Failed to get posts: Status code {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"Error fetching posts: {str(e)}")
        return False

def try_create_post(url, username, password):
    """Try to create a test draft post"""
    if not (url and username and password):
        return False
    
    url = url.rstrip('/')
    posts_url = f"{url}/wp-json/wp/v2/posts"
    
    try:
        print(f"\nTrying to create a test draft post...")
        post_data = {
            "title": "Test Post - Please Delete",
            "content": "<p>This is a test post created by the WordPress Diagnostic Tool.</p>",
            "status": "draft"
        }
        
        response = requests.post(
            posts_url,
            auth=(username, password),
            json=post_data,
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            post = response.json()
            post_id = post.get('id', 'Unknown')
            print(f"✓ Successfully created test post with ID: {post_id}")
            return True
        else:
            print(f"✗ Failed to create test post: Status code {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"✗ Error creating test post: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== WordPress Connection Diagnostic Tool ===\n")
    
    # Check environment variables
    wp_url, wp_username, wp_password = check_env_vars()
    
    # Test connection
    if test_connection(wp_url, wp_username, wp_password):
        print("\n✓ Basic connection and authentication successful!")
        
        # Check posts
        if check_posts(wp_url, wp_username, wp_password):
            print("\n✓ Successfully retrieved posts from WordPress!")
        
        # Ask to try creating post
        try_post = input("\nWould you like to try creating a test draft post? (y/n): ").lower()
        if try_post == 'y':
            if try_create_post(wp_url, wp_username, wp_password):
                print("\n✓ WordPress integration test completely successful!")
            else:
                print("\n✗ Post creation test failed, but authentication worked.")
    else:
        print("\n✗ WordPress connection test failed.")
        
        # Ask for manual credentials
        try_manual = input("\nWould you like to try with manually entered credentials? (y/n): ").lower()
        if try_manual == 'y':
            manual_url = input("WordPress URL (e.g., https://example.com): ")
            manual_username = input("Username: ")
            manual_password = input("Application Password: ")
            
            if test_connection(manual_url, manual_username, manual_password):
                print("\n✓ Manual connection successful! There may be an issue with your .env file.")
                print("Try updating your .env file with these credentials:")
                print(f"WORDPRESS_URL={manual_url}")
                print(f"WORDPRESS_USERNAME={manual_username}")
                print(f"WORDPRESS_APP_PASSWORD=[your password]")
