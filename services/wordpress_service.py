import os
import requests
from datetime import datetime
import re
import json
import logging
from dotenv import load_dotenv
import tempfile
from slugify import slugify
import html
import unicodedata

# Load environment variables with override to ensure latest values
load_dotenv(override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wordpress_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WordPress Service")

class WordPressService:
    """Service to publish articles to WordPress via its REST API"""
    
    def __init__(self, wordpress_url=None, username=None, app_password=None, site_name=None):
        """Initialize the WordPress service using environment variables or provided parameters"""
        load_dotenv(override=True)
        
        # Use provided parameters or fall back to environment variables
        self.wordpress_url = wordpress_url or os.getenv("WORDPRESS_URL")
        self.username = username or os.getenv("WORDPRESS_USERNAME")
        self.app_password = app_password or os.getenv("WORDPRESS_APP_PASSWORD")
        self.site_name = site_name or "Default WordPress"
        
        if not self.wordpress_url or not self.username or not self.app_password:
            logger.error("Missing WordPress credentials in environment variables")
            raise ValueError("Missing WordPress credentials. Please check your .env file.")
            
        # Make sure the WordPress URL doesn't end with a trailing slash
        if self.wordpress_url.endswith('/'):
            self.wordpress_url = self.wordpress_url[:-1]
            
        logger.info(f"Initialized WordPress service for {self.site_name}: {self.wordpress_url}")
        
        self.api_url = f"{self.wordpress_url}/wp-json/wp/v2"
        self.auth = (self.username, self.app_password)
        
        # Do not try to connect at initialization, wait for explicit request
        logger.info(f"WordPress service initialized with site: {self.wordpress_url}")
    
    def clean_html_for_wordpress(self, html_content):
        """
        Clean HTML content to make it compatible with WordPress
        """
        # Remove any potential script tags for security
        html_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
        
        # Extract the content from the blog-article wrapper if present
        article_pattern = re.compile(r'<article class="blog-article">(.*?)</article>', re.DOTALL)
        article_match = article_pattern.search(html_content)
        if article_match:
            html_content = article_match.group(1)
        
        # Remove style tags as WordPress has its own styling
        html_content = re.sub(r'<style.*?</style>', '', html_content, flags=re.DOTALL)
        
        return html_content
    
    def extract_featured_image_url(self, html_content):
        """
        Extract a potential image URL from the article to use as featured image
        Returns None if no suitable image is found
        """
        # Look for image suggestions in the content
        img_suggestion_match = re.search(r'Image suggestion:.*?https?://\S+', html_content, re.IGNORECASE)
        if img_suggestion_match:
            url_match = re.search(r'https?://\S+', img_suggestion_match.group(0))
            if url_match:
                return url_match.group(0)
        
        return None
    
    def upload_featured_image(self, image_url, title):
        """
        Upload an image from a URL to WordPress media library
        Returns the media ID if successful, None otherwise
        """
        try:
            # Download the image
            response = requests.get(image_url, stream=True)
            if response.status_code != 200:
                logger.warning(f"Failed to download image from {image_url}")
                return None
            
            # Get the filename from the URL
            filename = os.path.basename(image_url)
            if '?' in filename:
                filename = filename.split('?')[0]
            
            # If no extension, assume jpg
            if '.' not in filename:
                filename += '.jpg'
            
            # Upload to WordPress
            files = {'file': (filename, response.content)}
            headers = {
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
            
            wp_response = requests.post(
                f"{self.api_url}/media",
                auth=self.auth,
                headers=headers,
                files=files
            )
            
            if wp_response.status_code in (201, 200):
                return wp_response.json().get('id')
            else:
                logger.warning(f"Failed to upload featured image: {wp_response.status_code}, {wp_response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading featured image: {str(e)}")
            return None
    
    def get_or_create_category(self, category_name):
        """
        Get a category ID by name or create if it doesn't exist
        """
        try:
            # Try to find the category
            response = requests.get(
                f"{self.api_url}/categories",
                auth=self.auth,
                params={"search": category_name}
            )
            
            if response.status_code == 200:
                categories = response.json()
                for category in categories:
                    if category.get("name").lower() == category_name.lower():
                        return category.get("id")
            
            # If not found, create it
            create_response = requests.post(
                f"{self.api_url}/categories",
                auth=self.auth,
                json={"name": category_name}
            )
            
            if create_response.status_code in (201, 200):
                return create_response.json().get("id")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting/creating category: {str(e)}")
            return None
    
    def get_or_create_tag(self, tag_name):
        """
        Get a tag ID by name or create if it doesn't exist
        """
        try:
            # Try to find the tag
            response = requests.get(
                f"{self.api_url}/tags",
                auth=self.auth,
                params={"search": tag_name}
            )
            
            if response.status_code == 200:
                tags = response.json()
                for tag in tags:
                    if tag.get("name").lower() == tag_name.lower():
                        return tag.get("id")
            
            # If not found, create it
            create_response = requests.post(
                f"{self.api_url}/tags",
                auth=self.auth,
                json={"name": tag_name}
            )
            
            if create_response.status_code in (201, 200):
                return create_response.json().get("id")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting/creating tag: {str(e)}")
            return None
    
    def test_connection(self):
        """
        Test the connection to WordPress
        Returns True if successful, False otherwise
        """
        # Force reload environment variables to ensure latest values
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Update credentials from environment
        self.wordpress_url = os.getenv("WORDPRESS_URL", "").rstrip('/')
        self.username = os.getenv("WORDPRESS_USERNAME", "")
        self.app_password = os.getenv("WORDPRESS_APP_PASSWORD", "")
        self.api_url = f"{self.wordpress_url}/wp-json/wp/v2"
        self.auth = (self.username, self.app_password)
        
        logger.info(f"Testing connection to WordPress at {self.wordpress_url}")
        
        if not self.wordpress_url or not self.username or not self.app_password:
            logger.warning("WordPress credentials not configured in .env file")
            return False
            
        try:
            response = requests.get(
                f"{self.api_url}/posts", 
                params={"per_page": 1}, 
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"WordPress connection successful to {self.wordpress_url}")
                return True
            else:
                logger.warning(f"WordPress connection test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"WordPress connection error: {str(e)}")
            return False
    
    def clean_article_content(self, content):
        """
        Nettoie et répare le contenu HTML pour éviter les erreurs avec WordPress
        """
        if not content:
            return ""
            
        try:
            # Approche radicale pour le débogage
            # Simplifier drastiquement le HTML pour trouver une version qui fonctionne
            
            # 1. Normaliser les caractères
            content = unicodedata.normalize('NFC', content)
            
            # 2. Nettoyer agressivement le contenu
            # Supprimer toutes les balises potentiellement problématiques
            content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', '', content, flags=re.DOTALL)
            content = re.sub(r'<svg\b[^<]*(?:(?!<\/svg>)<[^<]*)*<\/svg>', '', content, flags=re.DOTALL)
            content = re.sub(r'<canvas\b[^<]*(?:(?!<\/canvas>)<[^<]*)*<\/canvas>', '', content, flags=re.DOTALL)
            
            # 3. Nettoyer les attributs potentiellement problématiques
            # Supprimer les attributs style, onclick, onload, etc.
            content = re.sub(r'\s+style\s*=\s*"[^"]*"', '', content)
            content = re.sub(r'\s+style\s*=\s*\'[^\']*\'', '', content)
            content = re.sub(r'\s+on\w+\s*=\s*"[^"]*"', '', content)
            content = re.sub(r'\s+on\w+\s*=\s*\'[^\']*\'', '', content)
            
            # 4. Simplifier encore plus si nécessaire pour le test
            if len(content) > 100000:  # Si très long
                # Extraire les sections importantes seulement
                paragraphs = re.findall(r'<p>.*?</p>', content, re.DOTALL)
                headings = re.findall(r'<h[1-6]>.*?</h[1-6]>', content, re.DOTALL)
                
                # Reconstruire avec seulement les paragraphes et titres
                simplified = ""
                for h in headings[:20]:  # Limiter le nombre de titres
                    simplified += h + "\n"
                for p in paragraphs[:100]:  # Limiter le nombre de paragraphes
                    simplified += p + "\n"
                
                if simplified:
                    content = simplified
                    
            # 5. Dernier recours - convertir en texte brut avec des balises p basiques
            if len(content) > 150000:
                plain_text = re.sub(r'<[^>]*>', '', content)
                paragraphs = plain_text.split('\n\n')
                content = ""
                for p in paragraphs[:200]:  # Limiter à 200 paragraphes
                    if p.strip():
                        content += f"<p>{p.strip()}</p>\n"
                        
            # Corriger les entités HTML
            content = html.unescape(content)
                
            return content
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du contenu: {str(e)}")
            # En cas d'erreur, retourner une version ultra simplifiée
            plain_text = re.sub(r'<[^>]*>', '', content[:30000])
            return f"<p>{plain_text[:5000]}</p>"
    
    def publish_article(self, article, video_url, categories=None, tags=None):
        """
        Publish an article to WordPress
        
        Args:
            article (dict): Article content
            video_url (str): YouTube video URL
            categories (list): List of category IDs
            tags (list): List of tag IDs
            
        Returns:
            dict: WordPress API response
        """
        if not self.wordpress_url or not self.username or not self.app_password:
            return {"status": "error", "error": "WordPress credentials not configured"}
            
        try:
            # Extract article content
            title = article.get("title", "Generated Article")
            content = article.get("content", "")
            excerpt = article.get("meta_description", "")
            
            # Log article details for debugging
            logger.info(f"Publishing article: {title}")
            logger.info(f"Content length: {len(content)} characters")
            print(f"Content starts with: {content[:200]}...")  # Debug
            
            # Nettoyer et réparer le contenu HTML
            content = self.clean_article_content(content)
            logger.info(f"Cleaned content length: {len(content)} characters")
            print(f"Cleaned content starts with: {content[:200]}...")  # Debug
            
            # Super-simplification pour test - Dernière tentative
            try:
                # Méthode 1: Juste le titre et pas de contenu
                minimal_post_data = {
                    'title': title,
                    'status': 'draft'
                }
                
                # Test avec un post minimal
                print("Essai avec post ultra-minimal...")
                minimal_response = requests.post(
                    f"{self.api_url}/posts",
                    json=minimal_post_data,
                    auth=self.auth,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                print(f"Résultat minimal: {minimal_response.status_code}")
                if minimal_response.status_code == 201:
                    post_id = minimal_response.json().get("id")
                    print(f"Post minimal créé avec ID: {post_id}")
                    
                    # Maintenant mettre à jour le contenu
                    print("Mise à jour avec contenu...")
                    update_response = requests.post(
                        f"{self.api_url}/posts/{post_id}",
                        json={'content': content},
                        auth=self.auth,
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    
                    print(f"Mise à jour contenu: {update_response.status_code}")
                    
                    # Ajouter l'extrait séparément
                    if excerpt:
                        excerpt_response = requests.post(
                            f"{self.api_url}/posts/{post_id}",
                            json={'excerpt': excerpt[:155]},
                            auth=self.auth,
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        print(f"Mise à jour extrait: {excerpt_response.status_code}")
                    
                    # Ajouter les catégories séparément
                    if categories:
                        cat_response = requests.post(
                            f"{self.api_url}/posts/{post_id}",
                            json={'categories': categories},
                            auth=self.auth,
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        print(f"Mise à jour catégories: {cat_response.status_code}")
                    
                    # Traiter la vidéo et la miniature
                    featured_image_id = 0
                    if video_url:
                        # Extract video ID from URL
                        video_id = None
                        if "youtube.com/watch?v=" in video_url:
                            video_id = video_url.split("youtube.com/watch?v=")[1].split("&")[0]
                        elif "youtu.be/" in video_url:
                            video_id = video_url.split("youtu.be/")[1].split("?")[0]
                            
                        if video_id:
                            # Ajouter le lien YouTube
                            video_link = f'<p><a href="https://www.youtube.com/watch?v={video_id}" target="_blank">Voir la vidéo sur YouTube</a></p>'
                            
                            # Mettre à jour avec le lien vidéo
                            video_response = requests.post(
                                f"{self.api_url}/posts/{post_id}",
                                json={'content': content + video_link},
                                auth=self.auth,
                                headers={'Content-Type': 'application/json'},
                                timeout=30
                            )
                            print(f"Ajout lien vidéo: {video_response.status_code}")
                            
                            # Essayer d'ajouter la miniature
                            try:
                                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                                featured_image_id = self.upload_thumbnail_from_url(thumbnail_url, title)
                                
                                if featured_image_id:
                                    # Mettre à jour l'image mise en avant
                                    img_response = requests.post(
                                        f"{self.api_url}/posts/{post_id}",
                                        json={'featured_media': featured_image_id},
                                        auth=self.auth,
                                        headers={'Content-Type': 'application/json'},
                                        timeout=30
                                    )
                                    print(f"Ajout image: {img_response.status_code}")
                            except Exception as img_error:
                                print(f"Erreur image: {str(img_error)}")
                    
                    return {
                        "status": "success", 
                        "post_id": post_id,
                        "featured_image_id": featured_image_id
                    }
                else:
                    print(f"Echec post minimal: {minimal_response.text[:500]}")
                
            except Exception as e:
                print(f"Erreur approche minimale: {str(e)}")
            
            # Si l'approche minimale a échoué, tentative classique
            # Create post with proper headers and timeout
            logger.info(f"Sending request to WordPress: {self.api_url}/posts")
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Approche classique simplifiée en dernier recours
            post_data = {
                'title': title,
                'content': content[:10000],  # Limité pour test
                'status': 'draft'
            }
            
            response = requests.post(
                f"{self.api_url}/posts",
                json=post_data,
                auth=self.auth,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"WordPress response status: {response.status_code}")
            print(f"WordPress response: {response.text[:500]}...")
            
            if response.status_code == 201:
                post_id = response.json().get("id")
                logger.info(f"Article published successfully with ID: {post_id}")
                
                # Si plus courte version a fonctionné, essayer d'ajouter plus
                if len(content) > 10000:
                    try:
                        update_response = requests.post(
                            f"{self.api_url}/posts/{post_id}",
                            json={'content': content},
                            auth=self.auth,
                            headers=headers,
                            timeout=60  # Prolonger le timeout
                        )
                        print(f"Update with full content: {update_response.status_code}")
                    except Exception as update_err:
                        print(f"Update error: {str(update_err)}")
                
                # Handle featured image in a separate request
                featured_image_id = 0
                video_id = None
                if video_url:
                    if "youtube.com/watch?v=" in video_url:
                        video_id = video_url.split("youtube.com/watch?v=")[1].split("&")[0]
                    elif "youtu.be/" in video_url:
                        video_id = video_url.split("youtu.be/")[1].split("?")[0]
                
                if post_id and video_id:
                    try:
                        # YouTube thumbnail URL
                        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                        featured_image_id = self.upload_thumbnail_from_url(thumbnail_url, title)
                        
                        if featured_image_id:
                            update_response = requests.post(
                                f"{self.api_url}/posts/{post_id}",
                                json={'featured_media': featured_image_id},
                                auth=self.auth,
                                headers=headers,
                                timeout=30
                            )
                    except Exception as img_error:
                        logger.error(f"Error setting featured image: {str(img_error)}")
                
                return {
                    "status": "success", 
                    "post_id": post_id,
                    "featured_image_id": featured_image_id
                }
            else:
                error_details = "Unknown error"
                try:
                    error_json = response.json()
                    if 'message' in error_json:
                        error_details = error_json['message']
                    logger.error(f"WordPress error details: {json.dumps(error_json, indent=2)}")
                    print(f"WordPress error: {error_details}")
                except:
                    error_details = response.text[:500]
                    
                return {
                    "status": "error", 
                    "error": f"Failed to create post: {response.status_code}", 
                    "details": error_details
                }
        
        except Exception as e:
            logger.error(f"Exception during WordPress publication: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
    
    def upload_thumbnail_from_url(self, thumbnail_url, title):
        """
        Upload a thumbnail image from a URL to WordPress
        
        Args:
            thumbnail_url (str): URL of the thumbnail image
            title (str): Title for the media
            
        Returns:
            int: Media ID if successful, 0 otherwise
        """
        try:
            # Download the image
            image_response = requests.get(thumbnail_url, timeout=10)
            if image_response.status_code != 200:
                # Try fallback thumbnail if maxresdefault fails
                thumbnail_url = thumbnail_url.replace("maxresdefault.jpg", "hqdefault.jpg")
                image_response = requests.get(thumbnail_url, timeout=10)
                
                if image_response.status_code != 200:
                    return 0
                    
            # Determine filename from URL
            image_filename = os.path.basename(thumbnail_url)
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=image_filename) as temp_file:
                temp_file.write(image_response.content)
                temp_file_path = temp_file.name
                
            try:
                # Upload the image to WordPress
                with open(temp_file_path, 'rb') as img_file:
                    # Create media item
                    media_endpoint = f"{self.api_url}/media"
                    
                    file_name = f"{slugify(title[:50])}-thumbnail.jpg"
                    
                    headers = {
                        'Content-Disposition': f'attachment; filename="{file_name}"',
                        'Content-Type': 'image/jpeg',
                    }
                    
                    response = requests.post(
                        media_endpoint,
                        headers=headers,
                        data=img_file.read(),
                        auth=self.auth
                    )
                    
                    if response.status_code in [200, 201]:
                        return response.json().get('id', 0)
                        
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
            return 0
            
        except Exception as e:
            logger.error(f"Error uploading thumbnail: {str(e)}")
            return 0
