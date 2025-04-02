"""
Supabase Service for YouTube Article Generator
Manages database interactions for projects, WordPress sites, and RSS channels
"""
import os
import logging
from dotenv import load_dotenv
# Replace supabase import with individual components
import postgrest
import gotrue
import storage3
import realtime
from urllib.parse import urljoin

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
            # Initialize individual components instead of the full client
            self.rest_url = urljoin(self.supabase_url, "/rest/v1/")
            self.auth_url = urljoin(self.supabase_url, "/auth/v1/")
            self.storage_url = urljoin(self.supabase_url, "/storage/v1/")
            
            # Initialize postgrest client for database operations
            self.postgrest_client = postgrest.PostgrestClient(
                self.rest_url,
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}"
                }
            )
            
            # Initialize storage client
            self.storage_client = storage3.StorageClient(
                self.storage_url,
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}"
                }
            )
            
            # Create a client-like interface for backward compatibility
            self.client = self
            
            logger.info("Supabase components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase components: {str(e)}")
            raise
    
    # Table method to maintain compatibility with original code
    def table(self, table_name):
        """Get a table reference for the PostgrestClient"""
        return TableWrapper(self.postgrest_client, table_name)
    
    # Project management
    def get_all_projects(self):
        """Get all projects"""
        try:
            response = self.table("projects").select("*").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting projects: {str(e)}")
            raise
    
    def get_project(self, project_id):
        """Get a specific project by ID"""
        try:
            response = self.table("projects").select("*").eq("id", project_id).execute()
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
            response = self.table("projects").insert(project_data).execute()
            logger.info(f"Created new project: {name}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise
    
    def update_project(self, project_id, data):
        """Update a project"""
        try:
            response = self.table("projects").update(data).eq("id", project_id).execute()
            logger.info(f"Updated project {project_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {str(e)}")
            raise
    
    def delete_project(self, project_id):
        """Delete a project"""
        try:
            response = self.table("projects").delete().eq("id", project_id).execute()
            logger.info(f"Deleted project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {str(e)}")
            raise
    
    # WordPress site management
    def get_wordpress_sites_for_project(self, project_id):
        """Get WordPress sites for a specific project"""
        try:
            response = self.table("wordpress_sites").select("*").eq("project_id", project_id).execute()
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
            response = self.table("wordpress_sites").insert(site_data).execute()
            logger.info(f"Created new WordPress site: {name} for project {project_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating WordPress site: {str(e)}")
            raise
    
    def update_wordpress_site(self, site_id, data):
        """Update a WordPress site"""
        try:
            response = self.table("wordpress_sites").update(data).eq("id", site_id).execute()
            logger.info(f"Updated WordPress site {site_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating WordPress site {site_id}: {str(e)}")
            raise
    
    def delete_wordpress_site(self, site_id):
        """Delete a WordPress site"""
        try:
            response = self.table("wordpress_sites").delete().eq("id", site_id).execute()
            logger.info(f"Deleted WordPress site {site_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting WordPress site {site_id}: {str(e)}")
            raise
    
    # RSS channel management
    def get_rss_channels_for_project(self, project_id):
        """Get RSS channels for a specific project"""
        try:
            response = self.table("rss_channels").select("*").eq("project_id", project_id).execute()
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
            response = self.table("rss_channels").insert(channel_data).execute()
            logger.info(f"Created new RSS channel: {channel_id} for project {project_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating RSS channel: {str(e)}")
            raise
    
    def update_rss_channel(self, channel_id, data):
        """Update an RSS channel"""
        try:
            response = self.table("rss_channels").update(data).eq("id", channel_id).execute()
            logger.info(f"Updated RSS channel {channel_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating RSS channel {channel_id}: {str(e)}")
            raise
    
    def delete_rss_channel(self, channel_id):
        """Delete an RSS channel"""
        try:
            response = self.table("rss_channels").delete().eq("id", channel_id).execute()
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
            response = self.table("published_articles").insert(article_data).execute()
            logger.info(f"Tracked published article: {title} for project {project_id}")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error tracking published article: {str(e)}")
            raise
    
    def get_published_articles_for_project(self, project_id):
        """Get published articles for a specific project"""
        try:
            response = self.table("published_articles").select("*").eq("project_id", project_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting published articles for project {project_id}: {str(e)}")
            raise
    
    def check_article_exists(self, video_url):
        """Check if an article has already been published for a video URL"""
        try:
            response = self.table("published_articles").select("*").eq("video_url", video_url).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking if article exists for video {video_url}: {str(e)}")
            raise

# Helper class to maintain the same API as the original Supabase client
class TableWrapper:
    """Wrapper for postgrest client to maintain API compatibility"""
    
    def __init__(self, postgrest_client, table_name):
        self.postgrest_client = postgrest_client
        self.table_name = table_name
        self.query = self.postgrest_client.from_(self.table_name)
    
    def select(self, fields="*"):
        """Select fields from the table"""
        self.query = self.postgrest_client.from_(self.table_name).select(fields)
        return self
    
    def insert(self, data):
        """Insert data into the table"""
        self.query = self.postgrest_client.from_(self.table_name).insert(data)
        return self
    
    def update(self, data):
        """Update data in the table"""
        self.query = self.postgrest_client.from_(self.table_name).update(data)
        return self
    
    def delete(self):
        """Delete from the table"""
        self.query = self.postgrest_client.from_(self.table_name).delete()
        return self
    
    def eq(self, column, value):
        """Add equality filter"""
        self.query = self.query.eq(column, value)
        return self
    
    def execute(self):
        """Execute the query"""
        response = self.query.execute()
        # Create a response object with data attribute for compatibility
        return type('Response', (), {'data': response.get('data', [])})
