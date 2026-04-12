"""
LinkedIn Post Generator

Generates brand-voiced LinkedIn posts incorporating industry news and
following professional content guidelines for maximum engagement.
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from openai import OpenAI

from .news_retriever import NewsItem


class LinkedInPost(BaseModel):
    """Structured LinkedIn post output."""
    hook: str  # Opening attention-grabber
    body: str  # Main content
    call_to_action: str  # Engagement prompt
    hashtags: List[str]
    full_post: str  # Complete formatted post
    character_count: int
    news_referenced: Optional[str] = None


class BrandVoice(BaseModel):
    """Brand voice characteristics for post generation."""
    brand_name: str
    industry: str
    tone: str = "professional"  # professional, casual, inspirational, educational
    values: List[str] = []
    tagline: Optional[str] = None


class LinkedInPostGenerator:
    """
    Generates LinkedIn posts with brand voice consistency and industry relevance.
    
    LinkedIn Post Best Practices Applied:
    - Hook within first 2 lines (before "see more")
    - 1,300-2,000 characters optimal length
    - Clear call-to-action
    - 3-5 relevant hashtags
    - Single-line paragraphs for readability
    - Emoji usage (subtle, professional)
    """
    
    # LinkedIn post guidelines
    MAX_LENGTH = 3000  # LinkedIn limit
    OPTIMAL_MIN = 1300
    OPTIMAL_MAX = 2000
    HASHTAG_COUNT = (3, 5)
    
    # Post templates by type
    POST_TYPES = {
        "news_commentary": "Share insights on industry news with your perspective",
        "thought_leadership": "Establish expertise with original insights",
        "company_update": "Share brand news and achievements",
        "educational": "Teach your audience something valuable",
        "engagement": "Ask questions and spark discussion",
    }
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the post generator.
        
        Args:
            openai_api_key: OpenAI API key for LLM generation
        """
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required for post generation")
        
        self.client = OpenAI(api_key=api_key)
    
    def generate_post(
        self,
        brand_voice: BrandVoice,
        news_item: Optional[NewsItem] = None,
        topic: Optional[str] = None,
        post_type: str = "news_commentary"
    ) -> LinkedInPost:
        """
        Generate a LinkedIn post with brand voice.
        
        Args:
            brand_voice: Brand characteristics for voice consistency
            news_item: Optional news item to reference
            topic: Optional custom topic if no news item
            post_type: Type of post to generate
            
        Returns:
            Structured LinkedInPost object
        """
        if not news_item and not topic:
            raise ValueError("Either news_item or topic must be provided")
        
        content_focus = news_item.summary if news_item else topic
        news_title = news_item.title if news_item else None
        
        prompt = self._build_prompt(brand_voice, content_focus, news_title, post_type)
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt(brand_voice)
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        generated_content = response.choices[0].message.content
        return self._parse_and_structure_post(generated_content, news_title)
    
    def _get_system_prompt(self, brand_voice: BrandVoice) -> str:
        """Build the system prompt with brand voice characteristics."""
        values_str = ", ".join(brand_voice.values) if brand_voice.values else "quality, innovation"
        tagline_str = f' The brand tagline is "{brand_voice.tagline}".' if brand_voice.tagline else ""
        
        return f"""You are a LinkedIn content specialist writing for {brand_voice.brand_name}, 
a company in the {brand_voice.industry} industry.{tagline_str}

Brand voice characteristics:
- Tone: {brand_voice.tone}
- Core values: {values_str}

LinkedIn post best practices you MUST follow:
1. Start with a compelling hook (first 2 lines are critical - they appear before "see more")
2. Use single-line paragraphs with line breaks for readability
3. Keep total length between 1,300-2,000 characters
4. Include a clear call-to-action at the end
5. Add 3-5 relevant hashtags
6. Use subtle, professional emoji (1-3 max)
7. Make it valuable - teach, inspire, or inform
8. Write in first person plural (we) or share personal insights
9. Avoid salesy language - focus on providing value

Output format:
HOOK: [2 lines max, attention-grabbing opener]

BODY: [Main content with single-line paragraphs]

CTA: [Call to action - question or engagement prompt]

HASHTAGS: [#hashtag1 #hashtag2 #hashtag3]"""

    def _build_prompt(
        self, 
        brand_voice: BrandVoice, 
        content_focus: str,
        news_title: Optional[str],
        post_type: str
    ) -> str:
        """Build the generation prompt."""
        post_description = self.POST_TYPES.get(post_type, self.POST_TYPES["news_commentary"])
        
        news_context = ""
        if news_title:
            news_context = f"""
Reference this news item:
Title: {news_title}
Summary: {content_focus}

Provide commentary and insights on this news from {brand_voice.brand_name}'s perspective."""
        else:
            news_context = f"""
Topic to address: {content_focus}

Share valuable insights on this topic from {brand_voice.brand_name}'s perspective."""

        return f"""Create a LinkedIn post for {brand_voice.brand_name}.

Post type: {post_type} - {post_description}
{news_context}

Remember:
- Make it relevant to professionals in {brand_voice.industry}
- Show expertise and thought leadership
- Maintain the brand's {brand_voice.tone} tone
- Focus on providing value, not selling"""

    def _parse_and_structure_post(
        self, 
        content: str, 
        news_title: Optional[str]
    ) -> LinkedInPost:
        """Parse the generated content into structured format."""
        hook = ""
        body = ""
        cta = ""
        hashtags = []
        
        lines = content.strip().split("\n")
        current_section = None
        
        for line in lines:
            line_stripped = line.strip()
            
            if line_stripped.startswith("HOOK:"):
                current_section = "hook"
                hook = line_stripped.replace("HOOK:", "").strip()
            elif line_stripped.startswith("BODY:"):
                current_section = "body"
                body = line_stripped.replace("BODY:", "").strip()
            elif line_stripped.startswith("CTA:"):
                current_section = "cta"
                cta = line_stripped.replace("CTA:", "").strip()
            elif line_stripped.startswith("HASHTAGS:"):
                hashtag_line = line_stripped.replace("HASHTAGS:", "").strip()
                hashtags = [h.strip() for h in hashtag_line.split() if h.startswith("#")]
            elif current_section == "hook" and line_stripped:
                hook += "\n" + line_stripped
            elif current_section == "body" and line_stripped:
                body += "\n\n" + line_stripped if body else line_stripped
            elif current_section == "cta" and line_stripped:
                cta += " " + line_stripped
        
        # Construct full post
        full_post = f"{hook}\n\n{body}\n\n{cta}\n\n{' '.join(hashtags)}"
        
        # Fallback if parsing failed
        if not hook and not body:
            full_post = content
            # Try to extract hashtags
            import re
            hashtags = re.findall(r'#\w+', content)
            hook = content.split('\n')[0] if content else ""
            body = content
            cta = ""
        
        return LinkedInPost(
            hook=hook,
            body=body,
            call_to_action=cta,
            hashtags=hashtags,
            full_post=full_post.strip(),
            character_count=len(full_post),
            news_referenced=news_title
        )
    
    def generate_batch(
        self,
        brand_voice: BrandVoice,
        news_items: List[NewsItem],
        post_type: str = "news_commentary"
    ) -> List[LinkedInPost]:
        """
        Generate multiple posts from a list of news items.
        
        Args:
            brand_voice: Brand characteristics
            news_items: List of news items to create posts for
            post_type: Type of posts to generate
            
        Returns:
            List of LinkedInPost objects
        """
        posts = []
        for item in news_items:
            try:
                post = self.generate_post(brand_voice, item, post_type=post_type)
                posts.append(post)
            except Exception as e:
                # Log but continue with other items
                print(f"Failed to generate post for '{item.title}': {e}")
                continue
        return posts


# Convenience function
def generate_linkedin_post(
    brand_name: str,
    industry: str,
    topic: str,
    tone: str = "professional",
    values: Optional[List[str]] = None,
    tagline: Optional[str] = None
) -> LinkedInPost:
    """
    Quick function to generate a LinkedIn post.
    
    Args:
        brand_name: Company name
        industry: Industry sector
        topic: Topic to write about
        tone: Voice tone (professional, casual, inspirational, educational)
        values: Brand values
        tagline: Brand tagline
        
    Returns:
        Generated LinkedInPost
    """
    generator = LinkedInPostGenerator()
    brand_voice = BrandVoice(
        brand_name=brand_name,
        industry=industry,
        tone=tone,
        values=values or [],
        tagline=tagline
    )
    return generator.generate_post(brand_voice, topic=topic, post_type="thought_leadership")
