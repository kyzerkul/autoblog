# -*- coding: utf-8 -*-
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import os
from dotenv import load_dotenv
import re
import sys
import codecs
import locale
from unidecode import unidecode

# Environment variables configuration for encoding
os.environ["LANG"] = "C.UTF-8"
os.environ["LC_ALL"] = "C.UTF-8"
os.environ["PYTHONIOENCODING"] = "utf-8"

# stdout configuration for UTF-8
if hasattr(sys.stdout, 'detach'):
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

try:
    locale.setlocale(locale.LC_ALL, "C.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    except locale.Error:
        pass

load_dotenv()

class MistralService:
    def __init__(self):
        # Hard-code the API key to avoid any encoding issues with environment variables
        self.api_key = "eYJSYMPtqrmnm1VlcaRL0N1On5pq60Ie"
        if not self.api_key:
            # Version without accents
            error_msg = "Mistral API key is not configured in the .env file"
            raise ValueError(error_msg)
        self.client = MistralClient(api_key=self.api_key)

    def clean_text(self, text):
        """Cleans text without converting accented characters"""
        if text is None:
            return ""
            
        # Convert to string and clean spaces and line breaks
        text = str(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def format_article(self, content):
        """Formats the article in HTML with rich formatting"""
        try:
            # Check that the content is a UTF-8 string
            if isinstance(content, bytes):
                content = content.decode('utf-8')
                
            # Clean text without removing accents
            content = self.clean_text(content)
            
            # Article wrapper with proper styling
            article_start = '<article class="blog-article">'
            article_end = '</article>'
            
            # Convert Markdown headers to HTML with proper styling
            content = re.sub(r'^# (.*?)$', r'<h1 class="article-title">\1</h1>', content, flags=re.MULTILINE)
            content = re.sub(r'^## (.*?)$', r'<h2 class="section-title">\1</h2>', content, flags=re.MULTILINE)
            content = re.sub(r'^### (.*?)$', r'<h3 class="subsection-title">\1</h3>', content, flags=re.MULTILINE)
            content = re.sub(r'^#### (.*?)$', r'<h4 class="minor-title">\1</h4>', content, flags=re.MULTILINE)
            
            # Convert bold and italic text
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
            
            # Convert bullet lists
            bullet_pattern = re.compile(r'^- (.*?)$', re.MULTILINE)
            if bullet_pattern.search(content):
                # Find all bullet list sections
                parts = []
                in_list = False
                lines = content.split('\n')
                
                for line in lines:
                    bullet_match = bullet_pattern.match(line)
                    if bullet_match:
                        if not in_list:
                            # Start a new list
                            parts.append('<ul class="bullet-list">')
                            in_list = True
                        # Add list item
                        parts.append(f'<li>{bullet_match.group(1)}</li>')
                    else:
                        if in_list:
                            # Close the list
                            parts.append('</ul>')
                            in_list = False
                        parts.append(line)
                
                if in_list:
                    # Close any open list
                    parts.append('</ul>')
                
                content = '\n'.join(parts)
            
            # Convert numbered lists
            numbered_pattern = re.compile(r'^(\d+)\. (.*?)$', re.MULTILINE)
            if numbered_pattern.search(content):
                # Find all numbered list sections
                parts = []
                in_list = False
                lines = content.split('\n')
                
                for line in lines:
                    numbered_match = numbered_pattern.match(line)
                    if numbered_match:
                        if not in_list:
                            # Start a new list
                            parts.append('<ol class="numbered-list">')
                            in_list = True
                        # Add list item
                        parts.append(f'<li>{numbered_match.group(2)}</li>')
                    else:
                        if in_list:
                            # Close the list
                            parts.append('</ol>')
                            in_list = False
                        parts.append(line)
                
                if in_list:
                    # Close any open list
                    parts.append('</ol>')
                
                content = '\n'.join(parts)
            
            # Convert simple tables (markdown format)
            table_pattern = re.compile(r'^\|(.*?)\|$', re.MULTILINE)
            if table_pattern.search(content):
                lines = content.split('\n')
                table_lines = []
                in_table = False
                table_html = []
                
                for i, line in enumerate(lines):
                    if table_pattern.match(line):
                        if not in_table:
                            in_table = True
                            table_html = ['<div class="table-responsive"><table class="table table-bordered">']
                        
                        # Skip separator lines (like |---|---|)
                        if re.match(r'^\|[\s\-\|]*$', line):
                            continue
                        
                        # Parse table row
                        cells = line.strip('|').split('|')
                        
                        # Determine if it's a header row (first row in table)
                        if in_table and len(table_html) == 1:
                            table_html.append('<thead><tr>')
                            for cell in cells:
                                table_html.append(f'<th>{cell.strip()}</th>')
                            table_html.append('</tr></thead><tbody>')
                        else:
                            table_html.append('<tr>')
                            for cell in cells:
                                table_html.append(f'<td>{cell.strip()}</td>')
                            table_html.append('</tr>')
                    else:
                        if in_table:
                            table_html.append('</tbody></table></div>')
                            in_table = False
                            lines[i-len(table_lines):i] = ['\n'.join(table_html)]
                            table_lines = []
                            table_html = []
                
                if in_table:
                    table_html.append('</tbody></table></div>')
                    lines[len(lines)-len(table_lines):] = ['\n'.join(table_html)]
                
                content = '\n'.join(lines)
            
            # Format FAQ sections with proper styling
            content = re.sub(r'## FAQ', r'<h2 class="faq-title">Frequently Asked Questions</h2><div class="faq-section">', content)
            
            # Find and format Q&A patterns
            qa_pattern = re.compile(r'\*\*Q: (.*?)\*\*\s+(.*?)(?=\s+\*\*Q:|$)', re.DOTALL)
            qa_matches = list(qa_pattern.finditer(content))
            
            if qa_matches:
                for match in reversed(qa_matches):
                    question = match.group(1)
                    answer = match.group(2).strip()
                    qa_html = f'<div class="faq-item">\n<h4 class="faq-question">{question}</h4>\n<div class="faq-answer"><p>{answer}</p></div>\n</div>'
                    content = content[:match.start()] + qa_html + content[match.end():]
                
                # Close FAQ section if it exists
                content = re.sub(r'<div class="faq-section">(.*?)(?=<h2|\Z)', r'<div class="faq-section">\1</div>', content, flags=re.DOTALL)
            
            # Process conclusion section with a special style
            content = re.sub(r'## Conclusion', r'<h2 class="conclusion-title">Conclusion</h2><div class="conclusion-section">', content)
            conclusion_pattern = re.compile(r'<h2 class="conclusion-title">.*?</div>\s*(?=<|\Z)', re.DOTALL)
            conclusion_match = conclusion_pattern.search(content)
            if conclusion_match:
                conclusion_text = conclusion_match.group(0)
                if not conclusion_text.endswith('</div>'):
                    content = content[:conclusion_match.end()] + '</div>' + content[conclusion_match.end():]
            
            # Convert paragraphs (do this last to avoid interfering with other conversions)
            paragraphs = []
            in_special_block = False  # To track if we're inside a list, table, etc.
            
            for line in content.split('\n'):
                if line.startswith('<') and ('ul>' in line or 'ol>' in line or 'li>' in line or 'table' in line or 'div class=' in line):
                    in_special_block = True
                    paragraphs.append(line)
                elif line.startswith('</') and ('ul>' in line or 'ol>' in line or 'table' in line or 'div' in line):
                    in_special_block = False
                    paragraphs.append(line)
                elif in_special_block:
                    paragraphs.append(line)
                elif line.strip() and not line.startswith('<h') and not line.endswith('</h'):
                    paragraphs.append(f'<p class="article-paragraph">{line}</p>')
                else:
                    paragraphs.append(line)
            
            content = '\n'.join(paragraphs)
            
            # Add CSS styles for the article
            css_styles = """
<style>
.blog-article {
    font-family: Georgia, serif;
    line-height: 1.6;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
}
.article-title {
    font-size: 2rem;
    margin-bottom: 1.5rem;
    color: #222;
    border-bottom: 2px solid #f0f0f0;
    padding-bottom: 0.8rem;
}
.section-title {
    font-size: 1.5rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
    color: #333;
    border-left: 4px solid #3498db;
    padding-left: 12px;
}
.subsection-title {
    font-size: 1.3rem;
    margin-top: 1.8rem;
    margin-bottom: 0.8rem;
    color: #444;
}
.minor-title {
    font-size: 1.1rem;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
    color: #555;
    font-style: italic;
}
.article-paragraph {
    margin-bottom: 1.2rem;
    font-size: 1rem;
    line-height: 1.7;
}
.bullet-list, .numbered-list {
    margin-bottom: 1.5rem;
    padding-left: 2rem;
}
.bullet-list li, .numbered-list li {
    margin-bottom: 0.5rem;
    line-height: 1.6;
}
.table-responsive {
    overflow-x: auto;
    margin-bottom: 2rem;
}
.table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1.5rem;
}
.table th {
    background-color: #f8f9fa;
    font-weight: bold;
    text-align: left;
    padding: 12px;
    border: 1px solid #dee2e6;
}
.table td {
    padding: 12px;
    border: 1px solid #dee2e6;
}
.faq-title {
    font-size: 1.5rem;
    margin-top: 2.5rem;
    margin-bottom: 1.5rem;
    color: #333;
    text-align: center;
    border-bottom: 2px solid #f0f0f0;
    padding-bottom: 0.5rem;
}
.faq-section {
    background-color: #f9f9f9;
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 2rem;
}
.faq-item {
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #eee;
    padding-bottom: 1rem;
}
.faq-item:last-child {
    border-bottom: none;
    padding-bottom: 0;
}
.faq-question {
    font-size: 1.1rem;
    color: #2c3e50;
    margin-bottom: 0.5rem;
}
.faq-answer {
    color: #555;
}
.conclusion-title {
    font-size: 1.5rem;
    margin-top: 2.5rem;
    margin-bottom: 1rem;
    color: #333;
    border-left: 4px solid #27ae60;
    padding-left: 12px;
}
.conclusion-section {
    background-color: #f8f8f8;
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 2rem;
    border-left: 4px solid #27ae60;
}
</style>
            """
            
            # Wrap the content in the article tags and add CSS
            final_content = css_styles + article_start + content + article_end
            
            return final_content
        except Exception as e:
            print(f"Formatting error: {str(e)}")
            return content

    def generate_article(self, transcript):
        """
        Generates a structured article from a transcript
        """
        try:
            # Clean transcript
            cleaned_transcript = self.clean_text(transcript)
            
            # If the transcript is very long, divide it into sections
            words = cleaned_transcript.split()
            max_words_per_section = 2000  # Increased from 1000 to handle more content at once
            sections = []
            
            for i in range(0, len(words), max_words_per_section):
                section = ' '.join(words[i:i + max_words_per_section])
                sections.append(section)
            
            # First request to generate metadata only
            metadata_prompt = self.clean_text(f"""
            Context:
            You are an expert SEO writer tasked with transforming YouTube video transcripts into detailed articles.
            
            For now, I ONLY need you to generate the H1 title and meta description for this video transcript.
            
            Requirements:
            1. SEO-optimized H1 title (50-60 characters) - must include the main keyword.
            2. SEO-optimized meta description (150-160 characters) - clear, engaging, and including the main keyword.
            
            Format your response EXACTLY like this, with no additional explanations:
            TITLE: [Your SEO-optimized H1 title here]
            META_DESCRIPTION: [Your SEO-optimized meta description here]
            
            Here's the video transcript excerpt:
            {cleaned_transcript[:2000]}
            """)
            
            # Create messages for Mistral API - metadata request
            metadata_messages = [
                ChatMessage(role="user", content=metadata_prompt)
            ]
            
            # Call Mistral API for metadata
            metadata_response = self.client.chat(
                model="mistral-large-latest",  # Using the most powerful model for highest quality
                messages=metadata_messages,
                max_tokens=500,
                temperature=0.7
            )
            
            # Extract metadata
            metadata_content = metadata_response.choices[0].message.content
            
            # Parse metadata
            title = "Generated Article"
            meta_description = ""
            
            title_match = re.search(r'TITLE:\s*(.*?)$', metadata_content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
            
            meta_match = re.search(r'META_DESCRIPTION:\s*(.*?)$', metadata_content, re.MULTILINE)
            if meta_match:
                meta_description = meta_match.group(1).strip()
            
            # Generate article content for each section and combine them
            full_article_content = ""
            
            # For very short transcripts, process everything at once
            if len(sections) <= 1:
                content_prompt = self.clean_text(f"""
                Context:
                You are an expert SEO writer tasked with transforming YouTube video transcripts into DETAILED, COMPREHENSIVE, and optimized articles. Each article must accurately cover ALL the information from the video while structuring it in a clear and engaging way.

                Generation Instructions:
                1. Article Structure and Length
                The article MUST be EXTENSIVE and COMPLETE in coverage:
                - Aim for a minimum of 1500-2000 words for shorter videos
                - For longer videos, aim for 2500-4000 words or more
                - NEVER summarize or condense important information
                - Include ALL details, examples, and points mentioned in the transcript

                The article should follow this structure:

                H1 title: {title}
                (Note: I've already created the title, DO NOT include it in your generated content. Start with the introduction.)

                1. Engaging introduction (150-250 words) summarizing the video and establishing why this topic matters.

                2. Detailed body content with AT LEAST 4-6 main sections, each with:
                   - H2 headings for main sections (at least 4-6 sections)
                   - Multiple H3 subheadings under each H2 (2-4 subheadings per section)
                   - Each section should be 300-500 words minimum
                   - Bullet points or numbered lists for key takeaways (at least 2-3 lists in the article)
                   - Tables for comparative data where appropriate
                   - Bold important terms, concepts and key phrases (at least 15-20 throughout)

                3. Extensive FAQ section with minimum 5-7 detailed Q&A pairs related to the content

                4. Clear, actionable conclusion (200-300 words) summarizing key points and encouraging reader interaction

                2. Comprehensive Content Development
                EXPAND on every point mentioned in the transcript:
                - Add context, examples, and explanations beyond what's directly stated
                - Transform brief mentions into full paragraphs
                - Develop implied ideas into explicit content
                - Include DETAILED explanations of processes, concepts, and terminology
                - Elaborate on every example, anecdote, or case study mentioned

                3. Advanced SEO Optimization
                Headings and Structure:
                - Proper use of H2, H3 to improve search rankings
                - Include keyword variations in headings
                - Short, impactful sentences for better readability
                - Use of secondary keywords and synonyms for natural SEO enhancement

                Rich Media and Engagement:
                - Suggest inserting relevant images with optimized alt tags
                - Include at least 3-4 descriptive image suggestions with alt text
                - Encourage engagement by ending with open-ended questions for readers

                4. Writing Tone and Style
                - Clear, informative, and engaging tone
                - Natural, flowing style for easy reading
                - Avoid unnecessary technical jargon unless required (and explain complex terms when used)

                Use Markdown formatting:
                ## for H2 headings
                ### for H3 headings
                **bold text** for important terms
                - for bullet points
                1. for numbered lists
                | Header | Header | for tables

                VERY IMPORTANT: BE COMPREHENSIVE AND DETAILED. The article should be substantially longer and more detailed than a typical blog post. NEVER OMIT INFORMATION from the transcript.

                Here's the full transcript to transform into a comprehensive article:
                {cleaned_transcript}
                """)
                
                # Create messages for Mistral API - content request
                content_messages = [
                    ChatMessage(role="user", content=content_prompt)
                ]
                
                # Call Mistral API for article content with increased token limit
                content_response = self.client.chat(
                    model="mistral-large-latest",  # Using the most powerful model
                    messages=content_messages,
                    max_tokens=8000,  # Doubled token limit for longer articles
                    temperature=0.7
                )
                
                # Extract article content
                full_article_content = self.clean_text(content_response.choices[0].message.content)
                
            else:
                # For longer transcripts, process each section separately
                section_contents = []
                
                # First section should include introduction
                first_section_prompt = self.clean_text(f"""
                Context:
                You are an expert SEO writer tasked with transforming YouTube video transcripts into DETAILED, COMPREHENSIVE, and optimized articles. This is PART 1 of a multi-part article generation.

                Generation Instructions:
                For this FIRST SECTION, create:
                
                1. A comprehensive introduction (200-300 words) that:
                   - Introduces the topic clearly
                   - Establishes why it matters
                   - Previews what the reader will learn
                   - Uses engaging language to hook the reader
                
                2. Begin the first 2-3 main content sections with:
                   - Clear H2 headings
                   - Multiple H3 subheadings
                   - Detailed paragraphs (at least 300-500 words per section)
                   - Bullet points for key concepts
                   - Bold important terms and phrases
                
                Write in a detailed, comprehensive style with extensive coverage of all information from this portion of the transcript. 
                
                DO NOT conclude the article as this is only part 1.
                
                Use Markdown formatting.
                
                Here's the first part of the transcript:
                {sections[0]}
                """)
                
                first_section_messages = [
                    ChatMessage(role="user", content=first_section_prompt)
                ]
                
                first_section_response = self.client.chat(
                    model="mistral-large-latest",
                    messages=first_section_messages,
                    max_tokens=8000,
                    temperature=0.7
                )
                
                section_contents.append(self.clean_text(first_section_response.choices[0].message.content))
                
                # Middle sections
                for i, section in enumerate(sections[1:-1], 1):
                    middle_section_prompt = self.clean_text(f"""
                    Context:
                    You are an expert SEO writer transforming a YouTube transcript into a detailed article. This is PART {i+1} of a multi-part article generation.
                    
                    For this MIDDLE SECTION, continue the article with:
                    
                    1. 2-3 more main content sections with:
                       - Clear H2 headings that flow naturally from previous sections
                       - Multiple H3 subheadings
                       - Detailed paragraphs (at least 300-500 words per section)
                       - Lists and tables where appropriate
                       - Bold important terms and phrases
                    
                    Write in a detailed, comprehensive style with extensive coverage of all information.
                    
                    DO NOT introduce the article or conclude it as this is a middle section.
                    
                    Use Markdown formatting.
                    
                    Previous section ended with: "{section_contents[-1][-150:]}"
                    
                    Here's the next part of the transcript:
                    {section}
                    """)
                    
                    middle_section_messages = [
                        ChatMessage(role="user", content=middle_section_prompt)
                    ]
                    
                    middle_section_response = self.client.chat(
                        model="mistral-large-latest",
                        messages=middle_section_messages,
                        max_tokens=8000,
                        temperature=0.7
                    )
                    
                    section_contents.append(self.clean_text(middle_section_response.choices[0].message.content))
                
                # Last section should include conclusion and FAQ
                last_section_prompt = self.clean_text(f"""
                Context:
                You are an expert SEO writer transforming a YouTube transcript into a detailed article. This is the FINAL PART of a multi-part article generation.
                
                For this FINAL SECTION:
                
                1. Complete any remaining content sections with:
                   - Clear H2 headings that flow naturally
                   - Multiple H3 subheadings
                   - Detailed paragraphs (at least 300-500 words per section)
                   
                2. Add a comprehensive FAQ section with:
                   - At least 5-7 detailed Q&A pairs relevant to the content
                   - Format as: **Q: Question?** followed by detailed answer
                
                3. Create a strong conclusion (200-300 words) that:
                   - Summarizes key points from the entire article
                   - Provides actionable takeaways
                   - Ends with an engaging question to encourage comments
                
                Write in a detailed, comprehensive style to properly finish the article.
                
                Previous section ended with: "{section_contents[-1][-150:]}"
                
                Use Markdown formatting.
                
                Here's the final part of the transcript:
                {sections[-1]}
                """)
                
                last_section_messages = [
                    ChatMessage(role="user", content=last_section_prompt)
                ]
                
                last_section_response = self.client.chat(
                    model="mistral-large-latest",
                    messages=last_section_messages,
                    max_tokens=8000,
                    temperature=0.7
                )
                
                section_contents.append(self.clean_text(last_section_response.choices[0].message.content))
                
                # Combine all sections into a single article
                full_article_content = "\n\n".join(section_contents)
            
            # Format article in HTML
            formatted_article = self.format_article(full_article_content)
            
            return {
                'title': title,
                'meta_description': meta_description,
                'content': formatted_article,
                'raw_content': full_article_content,
                'status': 'success'
            }

        except Exception as e:
            error_message = str(e)
            if "API key" in error_message.lower():
                error_message = "Authentication error with Mistral API"
            elif "rate limit" in error_message.lower():
                error_message = "Too many requests to Mistral API, please try again in a few minutes"
            
            return {
                'error': error_message,
                'status': 'error'
            }