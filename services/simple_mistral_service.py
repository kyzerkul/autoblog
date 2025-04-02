#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simplified Mistral Service - No formatting
"""
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

class SimpleMistralService:
    """Service to generate articles using Mistral AI without additional formatting"""
    
    def __init__(self):
        """Initialize the Mistral service using environment variables"""
        # Get API key from environment variables
        self.api_key = os.getenv("MISTRAL_API_KEY", "")
        
        if not self.api_key:
            raise ValueError("Mistral API key is not configured in the .env file")
            
        # Initialize Mistral client
        self.client = MistralClient(api_key=self.api_key)
    
    def generate_article(self, transcript):
        """
        Generate an article from a YouTube transcript
        
        Args:
            transcript (str): YouTube video transcript
            
        Returns:
            dict: Article data with status, title, meta_description, and content
        """
        try:
            # Aucune limite sur la longueur du transcript - utiliser tout
            cleaned_transcript = transcript
            
            # Create a system prompt that requests HTML output
            system_prompt = """
            You are a professional content writer specializing in creating articles based on YouTube video transcripts.
            
            Generate a high-quality comprehensive article based on the provided YouTube transcript, following these guidelines:
            
            1. Create a detailed and complete article covering ALL major points from the transcript.
            2. Aim for a VERY long, in-depth content - don't summarize or reduce length.
            3. Your goal is to create the most comprehensive article possible.
            4. Include a compelling title that includes the main topic and keywords.
            5. Write a concise meta description (max 155 characters) that summarizes the article.
            6. Format the article in clean HTML using proper tags (h1, h2, h3, p, ul, li, etc.).
            7. Break down complex topics into multiple sections with clear headings.
            8. Expand on each point in the transcript with additional context and explanation.
            9. Do not add CSS styles or classes, just use basic HTML.
            10. Include as much factual information from the transcript as possible.
            11. The article length should be proportional to the transcript length - longer transcripts should produce longer articles.
            
            Your response must follow this exact format:
            
            TITLE: The article title
            META_DESCRIPTION: The meta description
            
            <article>
            [Your complete HTML content here]
            </article>
            """

            # Create messages for API call
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Here is the transcript from a YouTube video. Please create a comprehensive, in-depth article based on it:\n\n{cleaned_transcript}")
            ]
            
            # Call Mistral API with maximum token limit
            response = self.client.chat(
                model="mistral-large-latest",
                messages=messages,
                max_tokens=16384,  # Augmenter au maximum la limite de tokens
                temperature=0.7
            )
            
            # Extract response content
            content = response.choices[0].message.content
            
            # Extract title and meta description
            title_match = re.search(r'TITLE:\s*(.*?)(?:\n|$)', content, re.IGNORECASE)
            meta_match = re.search(r'META_DESCRIPTION:\s*(.*?)(?:\n|$)', content, re.IGNORECASE)
            
            title = title_match.group(1).strip() if title_match else "Generated Article"
            meta_description = meta_match.group(1).strip() if meta_match else ""
            
            # Extract article content
            article_match = re.search(r'<article>(.*?)</article>', content, re.DOTALL | re.IGNORECASE)
            article_content = article_match.group(1).strip() if article_match else content
            
            # If no article tags found, try to extract content after META_DESCRIPTION
            if not article_match and meta_match:
                content_start = meta_match.end()
                article_content = content[content_start:].strip()
            
            # Return the result
            return {
                "status": "success",
                "title": title,
                "meta_description": meta_description,
                "content": article_content,
                "raw_content": content  # For debugging
            }
            
        except Exception as e:
            print(f"Error generating article: {str(e)}")
            return {"status": "error", "error": str(e)}
