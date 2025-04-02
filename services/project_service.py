"""
Project Service for YouTube Article Generator
Manages projects with WordPress sites and RSS channels
"""
import os
import logging
import threading
from .supabase_service import SupabaseService
from .wordpress_service import WordPressService
from .rss_service import RSSService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProjectService:
    """Service for managing projects with WordPress sites and RSS channels"""
    
    def __init__(self):
        """Initialize project service and load active projects"""
        self.supabase = SupabaseService()
        self.active_projects = {}
        self.project_lock = threading.Lock()
        
    def load_active_projects(self):
        """Load all active projects from Supabase"""
        try:
            with self.project_lock:
                # Clear existing active projects
                self.active_projects = {}
                
                # Get active projects
                projects = self.supabase.get_all_projects()
                active_projects = [p for p in projects if p.get("active", False)]
                
                for project in active_projects:
                    project_id = project["id"]
                    
                    # Get WordPress site for this project
                    wp_sites = self.supabase.get_wordpress_sites_for_project(project_id)
                    
                    if not wp_sites:
                        logger.warning(f"Project {project_id} has no WordPress site configured, skipping")
                        continue
                        
                    wp_site = wp_sites[0]  # Use the first WordPress site for now
                    
                    # Get RSS channels for this project
                    channels = self.supabase.get_rss_channels_for_project(project_id)
                    
                    # Create WordPress service for this project
                    wordpress_service = WordPressService(
                        site_url=wp_site["url"],
                        username=wp_site["username"],
                        app_password=wp_site["app_password"]
                    )
                    
                    # Create RSS service with this WordPress service
                    rss_service = RSSService(
                        wordpress_service=wordpress_service,
                        project_id=project_id
                    )
                    
                    # Store in active projects
                    self.active_projects[project_id] = {
                        "project": project,
                        "wordpress_site": wp_site,
                        "channels": channels,
                        "wordpress_service": wordpress_service,
                        "rss_service": rss_service,
                        "monitoring_threads": {}  # Will store active monitoring threads
                    }
                
                logger.info(f"Loaded {len(self.active_projects)} active projects")
                return self.active_projects
                
        except Exception as e:
            logger.error(f"Error loading projects: {str(e)}")
            raise
    
    def start_project_monitoring(self, project_id):
        """Start monitoring all channels for a specific project"""
        try:
            with self.project_lock:
                if project_id not in self.active_projects:
                    logger.warning(f"Project {project_id} not found in active projects")
                    return False
                
                project = self.active_projects[project_id]
                
                # Start monitoring for all channels
                for channel in project["channels"]:
                    if channel.get("monitoring_active", True):
                        channel_id = channel["channel_id"]
                        auto_publish = channel.get("auto_publish", True)
                        
                        logger.info(f"Starting monitoring for channel {channel_id} in project {project_id}")
                        
                        # Start monitoring with the project's RSS service
                        result = project["rss_service"].start_monitoring(
                            channel_id,
                            auto_publish=auto_publish
                        )
                        
                        if result:
                            # Store the monitoring thread
                            monitoring_thread = project["rss_service"].get_monitoring_thread(channel_id)
                            project["monitoring_threads"][channel_id] = monitoring_thread
                            logger.info(f"Successfully started monitoring for channel {channel_id} in project {project_id}")
                        else:
                            logger.warning(f"Channel {channel_id} in project {project_id} is already being monitored")
                
                return True
                
        except Exception as e:
            logger.error(f"Error starting project monitoring for project {project_id}: {str(e)}")
            raise
    
    def stop_project_monitoring(self, project_id):
        """Stop monitoring all channels for a specific project"""
        try:
            with self.project_lock:
                if project_id not in self.active_projects:
                    logger.warning(f"Project {project_id} not found in active projects")
                    return False
                
                project = self.active_projects[project_id]
                
                # Stop all monitoring threads
                project["rss_service"].stop_all_monitoring()
                
                # Clear monitoring threads
                project["monitoring_threads"] = {}
                
                logger.info(f"Stopped all monitoring for project {project_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error stopping project monitoring for project {project_id}: {str(e)}")
            raise
    
    def start_channel_monitoring(self, project_id, channel_id):
        """Start monitoring for a specific channel only"""
        try:
            with self.project_lock:
                if project_id not in self.active_projects:
                    logger.warning(f"Project {project_id} not found in active projects")
                    return False
                
                project = self.active_projects[project_id]
                
                # Find the specific channel
                channel_to_start = None
                for channel in project["channels"]:
                    if channel.get("id") == channel_id:
                        channel_to_start = channel
                        break
                
                if not channel_to_start:
                    logger.warning(f"Channel {channel_id} not found in project {project_id}")
                    return False
                
                # Start monitoring for this specific channel only
                channel_youtube_id = channel_to_start["channel_id"]
                auto_publish = channel_to_start.get("auto_publish", True)
                
                logger.info(f"Starting monitoring for channel {channel_id} in project {project_id}")
                
                # Start monitoring with the project's RSS service
                result = project["rss_service"].start_monitoring(
                    channel_youtube_id,
                    auto_publish=auto_publish
                )
                
                if result:
                    # Store the monitoring thread
                    monitoring_thread = project["rss_service"].get_monitoring_thread(channel_youtube_id)
                    project["monitoring_threads"][channel_youtube_id] = monitoring_thread
                    logger.info(f"Successfully started monitoring for channel {channel_id} in project {project_id}")
                    return True
                else:
                    logger.warning(f"Channel {channel_id} in project {project_id} is already being monitored")
                    return False
                
        except Exception as e:
            logger.error(f"Error starting channel monitoring for channel {channel_id} in project {project_id}: {str(e)}")
            raise
    
    def stop_channel_monitoring(self, project_id, channel_id):
        """Stop monitoring for a specific channel only"""
        try:
            with self.project_lock:
                if project_id not in self.active_projects:
                    logger.warning(f"Project {project_id} not found in active projects")
                    return False
                
                project = self.active_projects[project_id]
                
                # Find the specific channel
                channel_to_stop = None
                for channel in project["channels"]:
                    if channel.get("id") == channel_id:
                        channel_to_stop = channel
                        break
                
                if not channel_to_stop:
                    logger.warning(f"Channel {channel_id} not found in project {project_id}")
                    return False
                
                # Stop monitoring for this specific channel only
                channel_youtube_id = channel_to_stop["channel_id"]
                
                logger.info(f"Stopping monitoring for channel {channel_id} in project {project_id}")
                
                # Stop the monitoring in RSS service
                result = project["rss_service"].stop_monitoring(channel_youtube_id)
                
                if result:
                    # Remove from monitoring threads if present
                    if channel_youtube_id in project["monitoring_threads"]:
                        del project["monitoring_threads"][channel_youtube_id]
                    logger.info(f"Successfully stopped monitoring for channel {channel_id} in project {project_id}")
                    return True
                else:
                    logger.warning(f"Channel {channel_id} in project {project_id} is not being monitored")
                    return False
                
        except Exception as e:
            logger.error(f"Error stopping channel monitoring for channel {channel_id} in project {project_id}: {str(e)}")
            raise
    
    def create_project(self, name, wp_name, wp_url, wp_username, wp_password, channel_ids=None, auto_publish=True):
        """Create a new project with WordPress site and channels"""
        try:
            with self.project_lock:
                # Create project in Supabase
                project = self.supabase.create_project(name, active=True)
                
                if not project:
                    raise Exception("Failed to create project")
                    
                project_id = project["id"]
                
                # Create WordPress site for this project
                wp_site = self.supabase.create_wordpress_site(
                    project_id=project_id,
                    name=wp_name,
                    url=wp_url,
                    username=wp_username,
                    app_password=wp_password
                )
                
                # Add channels if provided
                channels = []
                if channel_ids:
                    for channel_id in channel_ids:
                        channel = self.supabase.create_rss_channel(
                            project_id=project_id,
                            channel_id=channel_id,
                            auto_publish=auto_publish,
                            monitoring_active=True
                        )
                        channels.append(channel)
                
                # Create WordPress service for this project
                wordpress_service = WordPressService(
                    site_url=wp_url,
                    username=wp_username,
                    app_password=wp_password
                )
                
                # Create RSS service with this WordPress service
                rss_service = RSSService(
                    wordpress_service=wordpress_service,
                    project_id=project_id
                )
                
                # Store in active projects
                self.active_projects[project_id] = {
                    "project": project,
                    "wordpress_site": wp_site,
                    "channels": channels,
                    "wordpress_service": wordpress_service,
                    "rss_service": rss_service,
                    "monitoring_threads": {}
                }
                
                # Start monitoring for this project
                self.start_project_monitoring(project_id)
                
                logger.info(f"Created project {project_id} with name {name}")
                return project_id
                
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise
    
    def add_channel_to_project(self, project_id, channel_id, auto_publish=True):
        """Add a channel to an existing project"""
        try:
            with self.project_lock:
                if project_id not in self.active_projects:
                    logger.warning(f"Project {project_id} not found in active projects")
                    return False
                
                # Create channel in Supabase
                channel = self.supabase.create_rss_channel(
                    project_id=project_id,
                    channel_id=channel_id,
                    auto_publish=auto_publish,
                    monitoring_active=True
                )
                
                # Add to project channels
                project = self.active_projects[project_id]
                project["channels"].append(channel)
                
                # Start monitoring for this channel
                result = project["rss_service"].start_monitoring(
                    channel_id,
                    auto_publish=auto_publish
                )
                
                if result:
                    # Store the monitoring thread
                    monitoring_thread = project["rss_service"].get_monitoring_thread(channel_id)
                    project["monitoring_threads"][channel_id] = monitoring_thread
                    logger.info(f"Successfully started monitoring for channel {channel_id} in project {project_id}")
                else:
                    logger.warning(f"Channel {channel_id} in project {project_id} is already being monitored")
                
                return channel
                
        except Exception as e:
            logger.error(f"Error adding channel to project {project_id}: {str(e)}")
            raise
    
    def get_project_status(self, project_id):
        """Get the status of a specific project"""
        try:
            # First check if the project is already loaded in memory
            with self.project_lock:
                if project_id not in self.active_projects:
                    # Try to fetch and load the project from Supabase
                    logger.info(f"Project {project_id} not in memory, fetching from database")
                    
                    # Get project from Supabase
                    project_data = self.supabase.get_project(project_id)
                    if not project_data:
                        logger.warning(f"Project {project_id} not found in database")
                        return None
                    
                    # Get WordPress site for this project
                    wp_sites = self.supabase.get_wordpress_sites_for_project(project_id)
                    if not wp_sites:
                        # Return basic project info without WordPress details
                        return {
                            "id": project_id,
                            "name": project_data["name"],
                            "is_active": project_data.get("active", True),
                            "created_at": project_data.get("created_at"),
                            "wordpress_site": None,
                            "channels": []
                        }
                    
                    wp_site = wp_sites[0]
                    
                    # Get channels for this project - directly from Supabase
                    channels = self.supabase.get_rss_channels_for_project(project_id)
                    
                    # Create WordPress service for this project
                    wordpress_service = WordPressService(
                        wordpress_url=wp_site["url"],
                        username=wp_site["username"],
                        app_password=wp_site["app_password"],
                        site_name=wp_site["name"]
                    )
                    
                    # Create RSS service
                    rss_service = RSSService(
                        wordpress_service=wordpress_service,
                        project_id=project_id
                    )
                    
                    # Store in active projects
                    self.active_projects[project_id] = {
                        "project": project_data,
                        "wordpress_site": wp_site,
                        "channels": channels,
                        "wordpress_service": wordpress_service,
                        "rss_service": rss_service,
                        "monitoring_threads": {}
                    }
                    
                # Now we should have the project in memory
                project = self.active_projects[project_id]
                
                # Get fresh channel data from Supabase for every status request
                channels = self.supabase.get_rss_channels_for_project(project_id)
                project["channels"] = channels
                
                # Prepare channel status info
                channels_status = []
                for channel in project["channels"]:
                    # Determine if the channel is being monitored
                    channel_youtube_id = channel["channel_id"]
                    is_monitoring = project["rss_service"].is_monitoring(channel_youtube_id)
                    
                    # Add monitoring status to channel info
                    channel_info = dict(channel)
                    channel_info["is_monitoring"] = is_monitoring
                    channels_status.append(channel_info)
                
                # Prepare project status
                status = {
                    "id": project_id,
                    "name": project["project"]["name"],
                    "wordpress_site": project["wordpress_site"],
                    "channels": channels_status,
                    "is_active": project["project"].get("active", True),
                    "created_at": project["project"].get("created_at")
                }
                
                return status
                
        except Exception as e:
            logger.error(f"Error getting project status for project {project_id}: {str(e)}")
            raise
    
    def get_all_projects_status(self):
        """Get the status of all projects"""
        try:
            with self.project_lock:
                statuses = []
                
                for project_id in self.active_projects:
                    status = self.get_project_status(project_id)
                    if status:
                        statuses.append(status)
                
                return statuses
                
        except Exception as e:
            logger.error(f"Error getting all projects status: {str(e)}")
            raise
    
    def start_all_projects(self):
        """Start monitoring for all active projects"""
        try:
            # Load active projects first
            self.load_active_projects()
            
            # Start monitoring for each project
            for project_id in self.active_projects:
                self.start_project_monitoring(project_id)
            
            logger.info(f"Started monitoring for all {len(self.active_projects)} active projects")
            return True
            
        except Exception as e:
            logger.error(f"Error starting all projects: {str(e)}")
            raise
    
    def stop_all_projects(self):
        """Stop monitoring for all active projects"""
        try:
            with self.project_lock:
                for project_id in self.active_projects:
                    self.stop_project_monitoring(project_id)
                
                logger.info(f"Stopped monitoring for all {len(self.active_projects)} active projects")
                return True
                
        except Exception as e:
            logger.error(f"Error stopping all projects: {str(e)}")
            raise
