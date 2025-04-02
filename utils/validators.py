import re

def validate_youtube_url(url):
    """
    Valide si une URL est une URL YouTube valide
    """
    # Patterns pour les URLs YouTube valides
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}$',
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}&.*$',
        r'^https?://(?:www\.)?youtu\.be/[\w-]{11}$'
    ]
    
    return any(re.match(pattern, url) for pattern in patterns)

def validate_channel_id(channel_id):
    """
    Valide si un ID de chaîne YouTube est valide
    """
    # Pattern pour les IDs de chaîne YouTube (24 caractères alphanumériques)
    pattern = r'^[A-Za-z0-9_-]{24}$'
    return bool(re.match(pattern, channel_id)) 