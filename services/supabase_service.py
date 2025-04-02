"""
Supabase Service for YouTube Article Generator
Manages database interactions for projects, WordPress sites, and RSS channels
"""
import os
import logging
from dotenv import load_dotenv
from supabase import create_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseService:
    """Service for interacting with Supabase database"""
    
    def __init__(self):
        """Initialize Supabase client with credentials from environment variables"""
        load_dotenv()
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase URL or key not found in environment variables")
            raise ValueError("Supabase URL or key not found in environment variables")
            
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise
    
    # Project management
    def get_all_projects(self):
        """Get all projects"""
        try:
            response = self.client.table("projects").select("*").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting projects: {str(e)}")
            raise
    
    def get_project(self, project_id):
        """Get a specific project by ID"""
        try:
            response = self.client.table("projects").select("*").eq("id", project_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {str(e)}")
            raise
    
    def create_project(self, name, active=True):
        """Create a new project"""
        try:
            project_data = {
                "name": name,
                "active": active
            }
            response = self.client.table("projects").insert(project_data).execute()
            logger.info(f"Created new project: {name}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise
    
    def update_project(self, project_id, data):
        """Update a project"""
        try:
            response = self.client.table("projects").update(data).eq("id", project_id).execute()
            logger.info(f"Updated project {project_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {str(e)}")
            raise
    
    def delete_project(self, project_id):
        """Delete a project"""
        try:
            response = self.client.table("projects").delete().eq("id", project_id).execute()
            logger.info(f"Deleted project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {str(e)}")
            raise
    
    # WordPress site management
    def get_wordpress_sites_for_project(self, project_id):
        """Get WordPress sites for a specific project"""
        try:
            response = self.client.table("wordpress_sites").select("*").eq("project_id", project_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting WordPress sites for project {project_id}: {str(e)}")
            raise
    
    def create_wordpress_site(self, project_id, name, url, username, app_password):
        """Create a new WordPress site for a project"""
        try:
            site_data = {
                "project_id": project_id,
                "name": name,
                "url": url,
                "username": username,
                "app_password": app_password
            }
            response = self.client.table("wordpress_sites").insert(site_data).execute()
            logger.info(f"Created new WordPress site: {name} for project {project_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating WordPress site: {str(e)}")
            raise
    
    def update_wordpress_site(self, site_id, data):
        """Update a WordPress site"""
        try:
            response = self.client.table("wordpress_sites").update(data).eq("id", site_id).execute()
            logger.info(f"Updated WordPress site {site_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating WordPress site {site_id}: {str(e)}")
            raise
    
    def delete_wordpress_site(self, site_id):
        """Delete a WordPress site"""
        try:
            response = self.client.table("wordpress_sites").delete().eq("id", site_id).execute()
            logger.info(f"Deleted WordPress site {site_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting WordPress site {site_id}: {str(e)}")
            raise
    
    # RSS channel management
    def get_rss_channels_for_project(self, project_id):
        """Get RSS channels for a specific project"""
        try:
            response = self.client.table("rss_channels").select("*").eq("project_id", project_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting RSS channels for project {project_id}: {str(e)}")
            raise
    
    def create_rss_channel(self, project_id, channel_id, channel_name=None, auto_publish=True, monitoring_active=True):
        """Create a new RSS channel for a project"""
        try:
            channel_data = {
                "project_id": project_id,
                "channel_id": channel_id,
                "channel_name": channel_name,
                "auto_publish": auto_publish,
                "monitoring_active": monitoring_active
            }
            response = self.client.table("rss_channels").insert(channel_data).execute()
            logger.info(f"Created new RSS channel: {channel_id} for project {project_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating RSS channel: {str(e)}")
            raise
    
    def update_rss_channel(self, channel_id, data):
        """Update an RSS channel"""
        try:
            response = self.client.table("rss_channels").update(data).eq("id", channel_id).execute()
            logger.info(f"Updated RSS channel {channel_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating RSS channel {channel_id}: {str(e)}")
            raise
    
    def delete_rss_channel(self, channel_id):
        """Delete an RSS channel"""
        try:
            response = self.client.table("rss_channels").delete().eq("id", channel_id).execute()
            logger.info(f"Deleted RSS channel {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting RSS channel {channel_id}: {str(e)}")
            raise
    
    # Published article tracking
    def track_published_article(self, project_id, video_url, article_url, title, status="published"):
        """Track a published article"""
        try:
            article_data = {
                "project_id": project_id,
                "video_url": video_url,
                "article_url": article_url,
                "title": title,
                "status": status
            }
            response = self.client.table("published_articles").insert(article_data).execute()
            logger.info(f"Tracked published article: {title} for project {project_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error tracking published article: {str(e)}")
            raise
    
    def get_published_articles_for_project(self, project_id):
        """Get published articles for a specific project"""
        try:
            response = self.client.table("published_articles").select("*").eq("project_id", project_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting published articles for project {project_id}: {str(e)}")
            raise
    
    def check_article_exists(self, video_url):
        """Check if an article has already been published for a video URL"""
        try:
            response = self.client.table("published_articles").select("*").eq("video_url", video_url).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking if article exists for video {video_url}: {str(e)}")
            raise
