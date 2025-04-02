from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable
from youtube_transcript_api.formatters import TextFormatter
from unidecode import unidecode
import re

class YouTubeService:
    def __init__(self):
        self.formatter = TextFormatter()

    def clean_text(self, text):
        """Cleans text while preserving special characters"""
        if text is None:
            return ""
            
        # Option 1: Preserve UTF-8 characters (recommended)
        # Clean only multiple spaces and line breaks
        text = re.sub(r'\s+', ' ', str(text)).strip()
        return text
        
        # Option 2: If necessary, use unidecode but without forcing ASCII
        # return unidecode(str(text))

    def get_video_id(self, url):
        """Extracts the video ID from a YouTube URL"""
        patterns = [
            r'(?:v=|\/videos\/)([^&\n?#]+)',
            r'(?:youtu\.be\/)([^&\n?#]+)',
            r'(?:embed\/)([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        raise ValueError("Invalid YouTube URL. Expected format: https://www.youtube.com/watch?v=VIDEO_ID")

    def get_transcript(self, url):
        """
        Retrieves the transcript of a YouTube video using youtube_transcript_api
        """
        try:
            video_id = self.get_video_id(url)
            
            # Retrieve transcript
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'fr'])
            except NoTranscriptFound:
                raise Exception("No transcript found for this video in English or French")
            except TranscriptsDisabled:
                raise Exception("Transcripts are disabled for this video")
            except VideoUnavailable:
                raise Exception("This video is unavailable or doesn't exist")
            
            # Convert to continuous text and clean
            transcript_text = self.formatter.format_transcript(transcript_list)
            transcript_text = self.clean_text(transcript_text)
            
            # Check minimum length
            if len(transcript_text.split()) < 50:
                raise Exception("The transcript is too short to generate a meaningful article")
            
            return transcript_text

        except ValueError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"Error retrieving transcript: {str(e)}")