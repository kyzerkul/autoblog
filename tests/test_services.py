import pytest
from services.youtube_service import YouTubeService
from services.mistral_service import MistralService
from services.rss_service import RSSService
from utils.validators import validate_youtube_url, validate_channel_id

# Tests pour les validateurs
def test_validate_youtube_url():
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share"
    ]
    invalid_urls = [
        "https://www.youtube.com/invalid",
        "https://example.com",
        "not_a_url"
    ]

    for url in valid_urls:
        assert validate_youtube_url(url) is True

    for url in invalid_urls:
        assert validate_youtube_url(url) is False

def test_validate_channel_id():
    valid_ids = [
        "UC_x5XG1OV2P6uZZ5FSM9Ttw",  # Google Developers
        "UC-9-kyTW8ZkP9HbVQMlJRfQ"   # Google
    ]
    invalid_ids = [
        "invalid",
        "123",
        "UC-9-kyTW8ZkP9HbVQMlJRfQ123"  # Trop long
    ]

    for channel_id in valid_ids:
        assert validate_channel_id(channel_id) is True

    for channel_id in invalid_ids:
        assert validate_channel_id(channel_id) is False

# Tests pour YouTubeService
@pytest.fixture
def youtube_service():
    return YouTubeService()

def test_get_video_id(youtube_service):
    urls = {
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ": "dQw4w9WgXcQ"
    }

    for url, expected_id in urls.items():
        assert youtube_service.get_video_id(url) == expected_id

    with pytest.raises(ValueError):
        youtube_service.get_video_id("https://example.com")

# Tests pour MistralService
@pytest.fixture
def mistral_service():
    return MistralService()

def test_generate_article(mistral_service):
    transcript = "Ceci est un exemple de transcription."
    result = mistral_service.generate_article(transcript)
    
    assert isinstance(result, dict)
    assert 'content' in result
    assert 'status' in result
    assert result['status'] == 'success'

# Tests pour RSSService
@pytest.fixture
def rss_service():
    return RSSService()

def test_get_channel_feed_url(rss_service):
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    expected_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    assert rss_service.get_channel_feed_url(channel_id) == expected_url

def test_process_video(rss_service):
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    rss_service.process_video(video_url)
    assert video_url in rss_service.processed_videos 