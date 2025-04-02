from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
from dotenv import load_dotenv
import os
import time
import json
import uuid
from datetime import datetime, timedelta
from services.youtube_service import YouTubeService
from services.simple_mistral_service import SimpleMistralService
from services.rss_service import RSSService
from services.wordpress_service import WordPressService
from services.scraper_service import ScraperService
from services.supabase_service import SupabaseService
from services.project_service import ProjectService
from utils.validators import validate_youtube_url
import json
from unidecode import unidecode
import sys
import locale
import html

# Encoding configuration
os.environ["LANG"] = "C.UTF-8"
os.environ["LC_ALL"] = "C.UTF-8"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Locale configuration attempt
try:
    locale.setlocale(locale.LC_ALL, "C.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    except locale.Error:
        # If standard locales don't work, try a fallback to system default
        try:
            locale.setlocale(locale.LC_ALL, '')  # Use system default locale
        except locale.Error:
            pass  # Continue even if we can't set the locale

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
app.json.ensure_ascii = False  # To handle UTF-8 characters correctly in JSON responses

# Flask encoding configuration
app.config['JSON_AS_ASCII'] = False

# Middleware to intercept all responses and ensure correct encoding
@app.after_request
def ensure_ascii(response):
    """
    Middleware to ensure all responses are correctly encoded
    """
    if response.mimetype == 'application/json':
        try:
            # Get JSON content
            data = json.loads(response.get_data(as_text=True))
            
            # Encode entire content
            # Use json.dumps directly without complex manipulation
            # This is the most reliable way to handle UTF-8 encoding
            response.set_data(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            
            # Set content header
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        except Exception as e:
            print(f"Encoding error: {str(e)}")
            # If an error occurs, leave the response unchanged
            pass
    
    return response

# Initialize services
youtube_service = YouTubeService()
mistral_service = SimpleMistralService()
wordpress_service = WordPressService()
rss_service = RSSService(wordpress_service=wordpress_service)
project_service = ProjectService()
scraper_service = ScraperService()

# Data directory
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(data_dir, exist_ok=True)
processed_file = os.path.join(data_dir, 'processed_videos.json')

def load_processed_videos():
    """Load the list of already processed videos"""
    try:
        if os.path.exists(processed_file):
            with open(processed_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        print(f"Error loading processed videos: {str(e)}")
        return []

def save_processed_videos(processed_videos):
    """Save the list of processed videos"""
    try:
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(processed_videos, f, indent=2)
    except Exception as e:
        print(f"Error saving processed videos: {str(e)}")

@app.route('/')
def index():
    """Application home page"""
    return render_template('index.html')

@app.route('/api/generate-article', methods=['POST'])
def generate_article():
    """Endpoint to generate an article from a YouTube URL"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"status": "error", "error": "Missing YouTube URL"}), 400

        youtube_url = data['url']
        if not validate_youtube_url(youtube_url):
            return jsonify({"status": "error", "error": "Invalid YouTube URL"}), 400

        publish_to_wordpress = data.get('publish_to_wordpress', False)
        categories = data.get('categories', [])

        # Extract transcript
        transcript = youtube_service.get_transcript(youtube_url)
        
        # Generate article with Mistral
        article = mistral_service.generate_article(transcript)
        
        # Publish to WordPress if requested
        if publish_to_wordpress and article.get('status') == 'success':
            try:
                wordpress_response = wordpress_service.publish_article(
                    article=article,
                    video_url=youtube_url,
                    categories=categories
                )
                
                if wordpress_response and wordpress_response.get('status') == 'success':
                    article['wordpress_post_id'] = wordpress_response.get('post_id')
                    article['wordpress_published'] = True
                    article['featured_image_id'] = wordpress_response.get('featured_image_id', 0)
                else:
                    article['wordpress_published'] = False
                    article['wordpress_error'] = wordpress_response.get('error', "Failed to publish to WordPress")
            except Exception as e:
                article['wordpress_published'] = False
                article['wordpress_error'] = str(e)
        
        # Use jsonify for proper encoding handling
        return jsonify(article)

    except Exception as e:
        # Use jsonify for error
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/autopilot/start', methods=['POST'])
def start_autopilot():
    """Start autopilot mode for a YouTube channel"""
    try:
        data = request.get_json()
        if not data or ('channel_id' not in data and 'rss_url' not in data):
            return jsonify({"status": "error", "error": "Missing channel ID or RSS URL"}), 400

        auto_publish = data.get('auto_publish', False)
        
        # Handle both RSS URL and channel ID
        if 'rss_url' in data:
            rss_url = data['rss_url']
            # Extract channel ID from RSS URL if needed
            if 'channel_id=' in rss_url:
                channel_id = rss_url.split('channel_id=')[1].split('&')[0]
            else:
                return jsonify({"status": "error", "error": "Invalid RSS URL format"}), 400
        else:
            channel_id = data['channel_id']
        
        # Start monitoring with better logging
        print(f"Starting autopilot for channel {channel_id} (auto_publish={auto_publish})")
        if rss_service.start_monitoring(channel_id, auto_publish=auto_publish):
            print(f"Successfully started monitoring for channel {channel_id}")
            return jsonify({
                "status": "success",
                "message": f"Autopilot started successfully for channel {channel_id}. Processing videos from the last 48 hours immediately."
            })
        else:
            print(f"Channel {channel_id} is already being monitored")
            return jsonify({
                "status": "info",
                "message": f"Channel {channel_id} is already being monitored"
            })

    except Exception as e:
        print(f"Error starting autopilot: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/autopilot/status', methods=['GET'])
def get_autopilot_status():
    """Get the status of all autopilot monitoring threads"""
    try:
        channels = rss_service.get_monitored_channels()
        return jsonify({
            "status": "success",
            "monitored_channels": channels
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/youtube/search', methods=['POST'])
def search_youtube():
    """Search YouTube for videos and generate articles"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"status": "error", "error": "Missing search query"}), 400

        query = data['query']
        max_results = data.get('max_results', 5)
        days_threshold = data.get('days_threshold', 7)
        auto_publish = data.get('auto_publish', False)
        categories = data.get('categories', [])
        
        # Calculate date threshold
        published_after = datetime.now() - timedelta(days=days_threshold)
        
        # Search for videos
        videos = scraper_service.search_videos(
            query=query, 
            max_results=max_results,
            published_after=published_after
        )
        
        if not videos:
            return jsonify({
                "status": "error", 
                "error": "No videos found for the query"
            }), 404
        
        # Process videos and track results
        processed_videos = load_processed_videos()
        results = []
        
        for video in videos:
            video_id = video['id']
            video_url = video['url']
            
            # Skip if already processed
            if video_id in processed_videos:
                results.append({
                    "video_id": video_id,
                    "title": video['title'],
                    "url": video_url,
                    "status": "skipped",
                    "message": "Video already processed"
                })
                continue
                
            try:
                # Get transcript
                transcript = youtube_service.get_transcript(video_url)
                
                if not transcript:
                    results.append({
                        "video_id": video_id,
                        "title": video['title'],
                        "url": video_url,
                        "status": "error",
                        "message": "No transcript available"
                    })
                    # Mark as processed to avoid retrying
                    processed_videos.append(video_id)
                    continue
                
                # Generate article
                article = mistral_service.generate_article(transcript)
                
                if not article or article.get('status') != 'success':
                    results.append({
                        "video_id": video_id,
                        "title": video['title'],
                        "url": video_url,
                        "status": "error",
                        "message": "Failed to generate article"
                    })
                    continue
                
                # Publish to WordPress if requested
                if auto_publish:
                    try:
                        wordpress_response = wordpress_service.publish_article(
                            article=article,
                            video_url=video_url,
                            categories=categories
                        )
                        
                        if wordpress_response and wordpress_response.get('status') == 'success':
                            results.append({
                                "video_id": video_id,
                                "title": video['title'],
                                "url": video_url,
                                "status": "success",
                                "message": "Article generated and published to WordPress",
                                "wordpress_post_id": wordpress_response.get('post_id')
                            })
                        else:
                            results.append({
                                "video_id": video_id,
                                "title": video['title'],
                                "url": video_url,
                                "status": "partial",
                                "message": f"Article generated but failed to publish to WordPress: {wordpress_response.get('error', 'Unknown error')}"
                            })
                    except Exception as e:
                        results.append({
                            "video_id": video_id,
                            "title": video['title'],
                            "url": video_url,
                            "status": "partial",
                            "message": f"Article generated but failed to publish to WordPress: {str(e)}"
                        })
                else:
                    results.append({
                        "video_id": video_id,
                        "title": video['title'],
                        "url": video_url,
                        "status": "success",
                        "message": "Article generated successfully"
                    })
                
                # Mark as processed
                processed_videos.append(video_id)
                
            except Exception as e:
                results.append({
                    "video_id": video_id,
                    "title": video['title'],
                    "url": video_url,
                    "status": "error",
                    "message": f"Error processing video: {str(e)}"
                })
        
        # Save processed videos
        save_processed_videos(processed_videos)
        
        return jsonify({
            "status": "success",
            "query": query,
            "results": results
        })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/rss/add-channel', methods=['POST'])
def add_rss_channel():
    """Add a channel to monitor via RSS"""
    try:
        data = request.get_json()
        if not data or 'channel_id' not in data:
            return jsonify({"status": "error", "error": "Missing channel ID"}), 400

        channel_id = data['channel_id']
        auto_publish = data.get('auto_publish', False)
        
        # Start monitoring
        result = rss_service.start_monitoring(channel_id, auto_publish=auto_publish)
        
        if result:
            return jsonify({
                "status": "success",
                "message": f"Channel {channel_id} added successfully"
            })
        else:
            return jsonify({
                "status": "error", 
                "error": "Failed to add channel. Check logs for details."
            }), 500

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/wordpress/test-connection', methods=['GET'])
def test_wordpress_connection():
    """Test WordPress connection with current credentials"""
    try:
        is_connected = wordpress_service.test_connection()
        
        if is_connected:
            return jsonify({
                "status": "success",
                "message": "WordPress connection successful",
                "site_url": wordpress_service.site_url
            })
        else:
            return jsonify({
                "status": "error", 
                "error": "Could not connect to WordPress. Check your credentials."
            }), 500

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/projects', methods=['GET'])
def projects_page():
    """Render the projects management page"""
    return render_template('projects.html')

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get all projects"""
    try:
        supabase = SupabaseService()
        projects = supabase.get_all_projects()
        
        return jsonify({
            "status": "success",
            "projects": projects
        })
    except Exception as e:
        print(f"Error getting projects: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["name", "wp_name", "wp_url", "wp_username", "wp_password"]
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "error": f"Missing required field: {field}"}), 400
        
        # Process YouTube channel/RSS URL
        channel_ids = []
        if "youtube_rss" in data and data["youtube_rss"]:
            rss_url = data["youtube_rss"]
            # Extract channel ID from RSS URL if provided
            if "channel_id=" in rss_url:
                channel_id = rss_url.split("channel_id=")[1].split("&")[0]
                channel_ids.append(channel_id)
            # Direct channel ID
            elif rss_url.startswith("UC"):
                channel_ids.append(rss_url)
            # Full URL without channel_id parameter
            else:
                channel_ids.append(rss_url)
        
        # Create project
        project_id = project_service.create_project(
            name=data["name"],
            wp_name=data["wp_name"],
            wp_url=data["wp_url"],
            wp_username=data["wp_username"],
            wp_password=data["wp_password"],
            channel_ids=channel_ids,
            auto_publish=data.get("auto_publish", True)
        )
        
        return jsonify({
            "status": "success",
            "message": "Project created successfully",
            "project_id": project_id
        })
    except Exception as e:
        print(f"Error creating project: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project"""
    try:
        project_status = project_service.get_project_status(project_id)
        
        if project_status:
            return jsonify({
                "status": "success",
                "project": project_status
            })
        else:
            return jsonify({"status": "error", "error": "Project not found"}), 404
    except Exception as e:
        print(f"Error getting project {project_id}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>/channels', methods=['POST'])
def add_channel(project_id):
    """Add a YouTube channel to a project"""
    try:
        # Get request data
        data = request.get_json()
        
        if not data or "channel_id" not in data:
            return jsonify({"status": "error", "error": "Channel ID is required"}), 400
            
        raw_channel_id = data["channel_id"]
        auto_publish = data.get("auto_publish", True)
        
        # Extract channel ID from RSS URL if necessary
        channel_id = raw_channel_id
        if "youtube.com/feeds/videos.xml" in raw_channel_id and "channel_id=" in raw_channel_id:
            # Extract the channel ID from the URL
            channel_id = raw_channel_id.split("channel_id=")[1].split("&")[0]
            print(f"Extracted channel ID: {channel_id} from URL: {raw_channel_id}")
        
        # Check if project exists
        supabase = SupabaseService()
        projects = supabase.client.table("projects").select("*").eq("id", project_id).execute()
        
        if not projects.data or len(projects.data) == 0:
            return jsonify({"status": "error", "error": "Project not found"}), 404
            
        # Check if channel already exists
        existing = supabase.client.table("rss_channels").select("*").eq("channel_id", channel_id).eq("project_id", project_id).execute()
        
        if existing.data and len(existing.data) > 0:
            return jsonify({"status": "error", "error": "Channel already exists in this project"}), 400
            
        # Add channel to project
        channel_data = {
            "project_id": project_id,
            "channel_id": channel_id,
            "auto_publish": auto_publish,
            "monitoring_active": False,
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.client.table("rss_channels").insert(channel_data).execute()
        
        if not result.data or len(result.data) == 0:
            return jsonify({"status": "error", "error": "Failed to add channel"}), 500
            
        new_channel = result.data[0]
        
        # Update project in memory if loaded
        if project_id in project_service.active_projects:
            project_service.get_project_status(project_id)
            
        return jsonify({
            "status": "success",
            "message": "Channel added successfully",
            "channel": new_channel
        })
    except Exception as e:
        print(f"Error adding channel: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>/start', methods=['POST'])
def start_project_monitoring(project_id):
    """Start monitoring for a specific project"""
    try:
        result = project_service.start_project_monitoring(project_id)
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Project monitoring started successfully"
            })
        else:
            return jsonify({"status": "error", "error": "Failed to start project monitoring"}), 500
    except Exception as e:
        print(f"Error starting project monitoring {project_id}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>/stop', methods=['POST'])
def stop_project_monitoring(project_id):
    """Stop monitoring for a specific project"""
    try:
        result = project_service.stop_project_monitoring(project_id)
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Project monitoring stopped successfully"
            })
        else:
            return jsonify({"status": "error", "error": "Failed to stop project monitoring"}), 500
    except Exception as e:
        print(f"Error stopping project monitoring {project_id}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        # Stop project monitoring first
        project_service.stop_project_monitoring(project_id)
        
        # Delete project from Supabase
        supabase = SupabaseService()
        result = supabase.delete_project(project_id)
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Project deleted successfully"
            })
        else:
            return jsonify({"status": "error", "error": "Failed to delete project"}), 500
    except Exception as e:
        print(f"Error deleting project {project_id}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>/wordpress/test', methods=['POST'])
def test_wp_connection(project_id):
    """Test WordPress connection for a project"""
    try:
        data = request.get_json()
        
        # Get WordPress site from project
        supabase = SupabaseService()
        wp_sites = supabase.get_wordpress_sites_for_project(project_id)
        
        if not wp_sites:
            return jsonify({"status": "error", "error": "WordPress site not found"}), 404
            
        wp_site = wp_sites[0]
        
        # Create temporary WordPress service
        wordpress_service = WordPressService(
            wordpress_url=wp_site["url"],
            username=wp_site["username"],
            app_password=wp_site["app_password"]
        )
        
        # Test connection
        result = wordpress_service.test_connection()
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Connection successful"
            })
        else:
            return jsonify({
                "status": "error", 
                "error": "Connection failed"
            }), 400
    except Exception as e:
        print(f"Error testing WordPress connection: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>/channels/<channel_id>/start', methods=['POST'])
def start_monitoring(project_id, channel_id):
    """Start monitoring for a channel"""
    try:
        # Get channel info
        supabase = SupabaseService()
        channels = supabase.client.table("rss_channels").select("*").eq("id", channel_id).execute()
        
        if not channels.data or len(channels.data) == 0:
            return jsonify({"status": "error", "error": "Channel not found"}), 404
            
        channel = channels.data[0]
        
        # Verify it belongs to the project
        if channel["project_id"] != project_id:
            return jsonify({"status": "error", "error": "Channel does not belong to project"}), 403
        
        # Mark as active
        supabase.client.table("rss_channels").update({"monitoring_active": True}).eq("id", channel_id).execute()
        
        # Start monitoring for THIS SPECIFIC CHANNEL ONLY
        result = project_service.start_channel_monitoring(project_id, channel_id)
        
        return jsonify({
            "status": "success",
            "message": "Monitoring started successfully"
        })
    except Exception as e:
        print(f"Error starting monitoring: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>/channels/<channel_id>/stop', methods=['POST'])
def stop_monitoring(project_id, channel_id):
    """Stop monitoring for a channel"""
    try:
        # Get channel info
        supabase = SupabaseService()
        channels = supabase.client.table("rss_channels").select("*").eq("id", channel_id).execute()
        
        if not channels.data or len(channels.data) == 0:
            return jsonify({"status": "error", "error": "Channel not found"}), 404
            
        channel = channels.data[0]
        
        # Verify it belongs to the project
        if channel["project_id"] != project_id:
            return jsonify({"status": "error", "error": "Channel does not belong to project"}), 403
        
        # Mark as inactive
        supabase.client.table("rss_channels").update({"monitoring_active": False}).eq("id", channel_id).execute()
        
        # Stop monitoring for THIS SPECIFIC CHANNEL ONLY
        result = project_service.stop_channel_monitoring(project_id, channel_id)
        
        return jsonify({
            "status": "success",
            "message": "Monitoring stopped successfully"
        })
    except Exception as e:
        print(f"Error stopping monitoring: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>/channels/<channel_id>/autopublish', methods=['POST'])
def toggle_autopublish(project_id, channel_id):
    """Toggle auto-publish setting for a channel"""
    try:
        # Get request data
        data = request.get_json()
        auto_publish = data.get("auto_publish", True)
        
        # Get channel info
        supabase = SupabaseService()
        channels = supabase.client.table("rss_channels").select("*").eq("id", channel_id).execute()
        
        if not channels.data or len(channels.data) == 0:
            return jsonify({"status": "error", "error": "Channel not found"}), 404
            
        channel = channels.data[0]
        
        # Verify it belongs to the project
        if channel["project_id"] != project_id:
            return jsonify({"status": "error", "error": "Channel does not belong to project"}), 403
        
        # Update auto-publish setting
        supabase.client.table("rss_channels").update({"auto_publish": auto_publish}).eq("id", channel_id).execute()
        
        # Update in memory if project is loaded
        if project_id in project_service.active_projects:
            project = project_service.active_projects[project_id]
            for ch in project.get("channels", []):
                if ch["id"] == channel_id:
                    ch["auto_publish"] = auto_publish
                    break
        
        return jsonify({
            "status": "success",
            "message": "Auto-publish setting updated successfully"
        })
    except Exception as e:
        print(f"Error updating auto-publish setting: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    """Update project details"""
    try:
        # Get request data
        data = request.get_json()
        
        # Prepare update data for project
        project_data = {}
        if "name" in data:
            project_data["name"] = data["name"]
        if "active" in data:
            project_data["active"] = data["active"]
            
        # Update project if we have data
        supabase = SupabaseService()
        if project_data:
            result = supabase.client.table("projects").update(project_data).eq("id", project_id).execute()
            
            if not result.data or len(result.data) == 0:
                return jsonify({"status": "error", "error": "Project not found"}), 404
        
        # Update WordPress site if provided
        if "wordpress_site" in data and data["wordpress_site"]:
            wp_site = data["wordpress_site"]
            site_id = wp_site.get("id")
            
            if site_id:
                site_data = {}
                if "name" in wp_site:
                    site_data["name"] = wp_site["name"]
                if "url" in wp_site:
                    site_data["url"] = wp_site["url"]
                if "username" in wp_site:
                    site_data["username"] = wp_site["username"]
                if "app_password" in wp_site and wp_site["app_password"]:
                    site_data["app_password"] = wp_site["app_password"]
                    
                if site_data:
                    supabase.client.table("wordpress_sites").update(site_data).eq("id", site_id).execute()
        
        # Update project in memory
        if project_id in project_service.active_projects:
            project_service.get_project_status(project_id)
            
        return jsonify({
            "status": "success",
            "message": "Project updated successfully"
        })
    except Exception as e:
        print(f"Error updating project: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/projects/<project_id>/articles', methods=['GET'])
def get_articles(project_id):
    """Get published articles for a project"""
    try:
        # Get articles from database
        supabase = SupabaseService()
        
        # Use select directly from table for better stability
        result = supabase.client.table("published_articles").select("*").eq("project_id", project_id).execute()
        
        articles = result.data if result.data else []
        
        return jsonify({
            "status": "success",
            "articles": articles
        })
    except Exception as e:
        print(f"Error fetching articles: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

# Start all projects when the application starts
def start_all_projects():
    """Start monitoring for all active projects when the application starts"""
    try:
        project_service.load_active_projects()
        print("Active projects loaded")
    except Exception as e:
        print(f"Error starting all projects: {str(e)}")

# Call start_all_projects() directly instead of using a decorator
# Comment this out temporarily until we resolve route issues
# start_all_projects()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')