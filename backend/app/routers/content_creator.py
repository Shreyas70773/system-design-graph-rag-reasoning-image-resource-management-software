"""
AI-Powered LinkedIn Content Creator Router

A comprehensive content creation platform that:
1. Searches the internet for industry-relevant topics using Perplexity (sonar model)
2. Generates personalized LinkedIn post ideas and full drafts
3. Analyzes profile and past posts for personalized suggestions
4. Creates long-form content tailored to engagement goals
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import os
from datetime import datetime

from app.config import get_settings

router = APIRouter()


# ===================
# REQUEST/RESPONSE MODELS
# ===================

class ContentGoal(BaseModel):
    """User's content goal"""
    goal_type: str = Field("engagement", description="engagement, job_search, followers, leads, thought_leadership")
    target_audience: Optional[str] = None
    tone: str = Field("professional", description="professional, casual, inspirational, educational, humorous")


class BrandProfile(BaseModel):
    """Brand/personal profile for content personalization"""
    name: str
    industry: str
    tagline: Optional[str] = None
    values: List[str] = []
    products_services: List[str] = []
    past_topics: List[str] = []  # Topics from previous successful posts
    bio: Optional[str] = None


class TrendingTopic(BaseModel):
    """A trending topic found via internet search"""
    title: str
    summary: str
    why_relevant: str
    source: Optional[str] = None
    engagement_potential: str = "medium"  # low, medium, high


class ContentIdea(BaseModel):
    """A content idea with hook and outline"""
    hook: str
    main_topic: str
    key_points: List[str]
    call_to_action: str
    estimated_engagement: str
    content_type: str  # story, tips, opinion, news_commentary, question, celebration


class GeneratedPost(BaseModel):
    """A fully generated LinkedIn post"""
    content: str
    hook: str
    hashtags: List[str]
    estimated_reach: str
    best_posting_time: str
    variations: List[str] = []  # Alternative versions


class ContentDiscoveryRequest(BaseModel):
    """Request to discover trending topics"""
    profile: BrandProfile
    goals: ContentGoal = ContentGoal()
    num_topics: int = Field(5, ge=1, le=10)
    focus_areas: List[str] = []  # Specific areas to focus on


class ContentDiscoveryResponse(BaseModel):
    """Response with discovered topics"""
    success: bool
    topics: List[TrendingTopic]
    personalized_angles: List[str]
    search_sources: List[str]


class GenerateIdeasRequest(BaseModel):
    """Request to generate content ideas"""
    profile: BrandProfile
    goals: ContentGoal = ContentGoal()
    num_ideas: int = Field(5, ge=1, le=10)
    trending_topic: Optional[str] = None  # Optional topic to base ideas on


class GenerateIdeasResponse(BaseModel):
    """Response with content ideas"""
    success: bool
    ideas: List[ContentIdea]
    daily_suggestion: str


class GeneratePostRequest(BaseModel):
    """Request to generate a full LinkedIn post"""
    profile: BrandProfile
    goals: ContentGoal = ContentGoal()
    topic: Optional[str] = None
    content_idea: Optional[ContentIdea] = None
    style: str = Field("storytelling", description="storytelling, listicle, question, hot_take, educational")
    include_emoji: bool = True
    max_length: int = Field(1300, description="Max characters (LinkedIn limit is ~3000)")
    generate_variations: bool = False


class GeneratePostResponse(BaseModel):
    """Response with generated post"""
    success: bool
    post: GeneratedPost
    editing_suggestions: List[str]


class DailyContentPlanRequest(BaseModel):
    """Request for a daily content plan"""
    profile: BrandProfile
    goals: ContentGoal = ContentGoal()
    days: int = Field(7, ge=1, le=30)


class DailyContentItem(BaseModel):
    """A single day's content plan"""
    day: int
    date: str
    topic: str
    content_type: str
    hook: str
    best_time: str


class DailyContentPlanResponse(BaseModel):
    """Response with daily content plan"""
    success: bool
    plan: List[DailyContentItem]
    themes: List[str]


# ===================
# HELPER FUNCTIONS
# ===================

async def perplexity_search(query: str, system_prompt: str, api_key: str) -> Dict[str, Any]:
    """Execute a Perplexity search with the sonar model"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar",  # Using sonar model for online search
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
        )
        
        if response.status_code != 200:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Perplexity API error: {error_data}"
            )
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = data.get("citations", [])
        
        return {"content": content, "sources": citations}


# ===================
# ENDPOINTS
# ===================

@router.post("/discover-topics", response_model=ContentDiscoveryResponse)
async def discover_trending_topics(request: ContentDiscoveryRequest):
    """
    Discover trending topics in your industry using Perplexity AI.
    
    Searches the internet for:
    - Recent industry news and developments
    - Viral content in your niche
    - Emerging trends and discussions
    - Topics your target audience cares about
    """
    settings = get_settings()
    api_key = settings.perplexity_api_key
    
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Perplexity API key not configured. Add PERPLEXITY_API_KEY to environment."
        )
    
    # Build search context
    focus = ", ".join(request.focus_areas) if request.focus_areas else request.profile.industry
    products = ", ".join(request.profile.products_services[:3]) if request.profile.products_services else ""
    
    system_prompt = """You are an expert LinkedIn content strategist and trend analyst. 
Your job is to find trending topics and news that would make excellent LinkedIn posts.
Focus on topics that drive engagement, spark discussions, and position the poster as a thought leader.
Always search for the most recent and relevant information."""

    query = f"""Search for the top {request.num_topics} trending topics and recent developments in the {request.profile.industry} industry.

Brand/Professional Context:
- Name: {request.profile.name}
- Industry: {request.profile.industry}
- Focus areas: {focus}
{f'- Products/Services: {products}' if products else ''}
{f'- Values: {", ".join(request.profile.values)}' if request.profile.values else ''}

Content Goal: {request.goals.goal_type}
Target Audience: {request.goals.target_audience or 'Industry professionals'}

For each topic, provide:
1. TOPIC: [Clear title]
2. SUMMARY: [2-3 sentence summary of what's happening]
3. WHY_RELEVANT: [Why this matters to the target audience]
4. ENGAGEMENT_POTENTIAL: [high/medium/low - based on how likely it is to generate engagement]

Also suggest 3 unique angles this specific professional could take on these topics."""

    try:
        result = await perplexity_search(query, system_prompt, api_key)
        content = result["content"]
        sources = result["sources"]
        
        # Parse topics from response using improved regex-based parsing
        import re
        topics = []
        
        # Try to find numbered topics with various formats
        # Pattern matches: "### 1. TOPIC:", "1. TOPIC:", "**1. TOPIC:**", "1. **TOPIC:**", etc.
        topic_pattern = r'(?:###?\s*)?(?:\*\*)?(\d+)[\.\)]\s*(?:TOPIC:?\s*)?(?:\*\*)?\s*(.+?)(?:\*\*)?(?:\n|$)'
        summary_pattern = r'(?:\*\*)?SUMMARY:?\*?\*?\s*(.+?)(?=(?:\*\*)?(?:WHY|ENGAGEMENT|###|\d+\.|$))'
        why_pattern = r'(?:\*\*)?WHY[_\s]?RELEVANT:?\*?\*?\s*(.+?)(?=(?:\*\*)?(?:ENGAGEMENT|###|\d+\.|$))'
        engagement_pattern = r'(?:\*\*)?ENGAGEMENT[_\s]?POTENTIAL:?\*?\*?\s*(high|medium|low)'
        
        # Split content by topic numbers
        topic_sections = re.split(r'(?=(?:###?\s*)?\*?\*?(?:\d+)[\.\)])', content, flags=re.IGNORECASE)
        
        for section in topic_sections:
            if not section.strip():
                continue
                
            topic = {}
            
            # Extract title - look for the topic heading
            title_match = re.search(r'(?:###?\s*)?(?:\*\*)?(\d+)[\.\)]\s*(?:TOPIC:?\s*)?(?:\*\*)?\s*([^\n\*]+)', section, re.IGNORECASE)
            if title_match:
                title = title_match.group(2).strip()
                # Clean up markdown artifacts
                title = re.sub(r'\*+', '', title).strip()
                title = re.sub(r'^TOPIC:?\s*', '', title, flags=re.IGNORECASE).strip()
                if title:
                    topic["title"] = title[:200]  # Limit title length
            
            # Extract summary
            summary_match = re.search(r'(?:\*\*)?SUMMARY:?\*?\*?\s*([^\*\n][^\n]+(?:\n(?![A-Z_]+:)[^\n]+)*)', section, re.IGNORECASE)
            if summary_match:
                summary = summary_match.group(1).strip()
                summary = re.sub(r'\*+', '', summary).strip()
                topic["summary"] = summary[:500]
            elif topic.get("title"):
                # Use remaining content as summary if no explicit SUMMARY
                remaining = re.sub(r'(?:###?\s*)?\d+[\.\)].*?\n', '', section, count=1)
                remaining = re.sub(r'\*\*[A-Z_]+:\*\*.*', '', remaining, flags=re.IGNORECASE)
                remaining = re.sub(r'\*+', '', remaining).strip()
                if remaining:
                    topic["summary"] = remaining[:500]
            
            # Extract why relevant
            why_match = re.search(r'(?:\*\*)?WHY[_\s]?RELEVANT:?\*?\*?\s*([^\n]+(?:\n(?![A-Z_]+:)[^\n]+)*)', section, re.IGNORECASE)
            if why_match:
                why = why_match.group(1).strip()
                why = re.sub(r'\*+', '', why).strip()
                topic["why_relevant"] = why[:300]
            else:
                topic["why_relevant"] = "Relevant to your industry and audience"
            
            # Extract engagement potential
            eng_match = re.search(r'(?:\*\*)?ENGAGEMENT[_\s]?POTENTIAL:?\*?\*?\s*(high|medium|low)', section, re.IGNORECASE)
            if eng_match:
                topic["engagement_potential"] = eng_match.group(1).lower()
            else:
                topic["engagement_potential"] = "medium"
            
            # Only add if we have title and summary
            if topic.get("title") and topic.get("summary"):
                topics.append(TrendingTopic(**topic))
        
        # Fallback: If parsing failed, try splitting by double newlines
        if not topics:
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and len(p.strip()) > 50]
            for i, para in enumerate(paragraphs[:request.num_topics]):
                # Clean markdown
                clean_para = re.sub(r'\*+', '', para).strip()
                clean_para = re.sub(r'###?\s*', '', clean_para).strip()
                
                # Try to extract a title from the first line
                lines = clean_para.split('\n')
                title = lines[0][:100] if lines else f"Trending Topic {i+1}"
                summary = '\n'.join(lines[1:])[:400] if len(lines) > 1 else clean_para[:400]
                
                topics.append(TrendingTopic(
                    title=title,
                    summary=summary or clean_para[:400],
                    why_relevant="Industry relevant topic discovered via search",
                    engagement_potential="medium"
                ))
        
        # Extract personalized angles
        angles = []
        content_lines = content.split("\n")
        if "angle" in content.lower() or "unique" in content.lower():
            for line in content_lines:
                if "angle" in line.lower() or line.startswith("-") or line.startswith("•"):
                    clean = line.strip("-•* ").strip()
                    if len(clean) > 20:
                        angles.append(clean)
        
        if not angles:
            angles = [
                f"Share your {request.profile.industry} perspective on this trend",
                f"Connect this to {request.profile.name}'s mission and values",
                f"Offer actionable advice for your audience"
            ]
        
        return ContentDiscoveryResponse(
            success=True,
            topics=topics[:request.num_topics],
            personalized_angles=angles[:5],
            search_sources=sources[:5] if sources else []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-ideas", response_model=GenerateIdeasResponse)
async def generate_content_ideas(request: GenerateIdeasRequest):
    """
    Generate personalized LinkedIn content ideas.
    
    Uses AI to create:
    - Attention-grabbing hooks
    - Content outlines with key points
    - Calls to action
    - Engagement predictions
    """
    settings = get_settings()
    api_key = settings.perplexity_api_key
    
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Perplexity API key not configured."
        )
    
    past_topics = ", ".join(request.profile.past_topics[:5]) if request.profile.past_topics else "None provided"
    
    system_prompt = """You are an expert LinkedIn content strategist who specializes in creating viral, engaging posts.
You understand what drives engagement on LinkedIn: storytelling, controversial opinions, practical advice, and authentic insights.
Generate content ideas that are specific, actionable, and tailored to the user's brand and goals."""

    topic_context = f"Focus on this trending topic: {request.trending_topic}" if request.trending_topic else "Generate diverse topics"
    
    query = f"""Generate {request.num_ideas} LinkedIn content ideas for:

Profile:
- Name: {request.profile.name}
- Industry: {request.profile.industry}
- Bio: {request.profile.bio or 'Not provided'}
- Values: {", ".join(request.profile.values) if request.profile.values else 'Not specified'}
- Past successful topics: {past_topics}

Goal: {request.goals.goal_type}
Tone: {request.goals.tone}
Target Audience: {request.goals.target_audience or 'Industry professionals'}

{topic_context}

For each idea, provide:
1. HOOK: [An attention-grabbing first line that stops scrollers]
2. TOPIC: [Main topic/theme]
3. KEY_POINTS: [3 bullet points to cover]
4. CTA: [Call to action to drive engagement]
5. TYPE: [story/tips/opinion/news_commentary/question/celebration]
6. ENGAGEMENT: [high/medium/low prediction]

Also provide a DAILY_SUGGESTION: One specific post idea they could write TODAY."""

    try:
        result = await perplexity_search(query, system_prompt, api_key)
        content = result["content"]
        
        # Parse ideas from response
        ideas = []
        current_idea = {}
        key_points = []
        
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("HOOK:") or (line.startswith("**") and "hook" in line.lower()):
                if current_idea.get("hook") and current_idea.get("main_topic"):
                    current_idea["key_points"] = key_points if key_points else ["Key insight 1", "Key insight 2", "Key insight 3"]
                    ideas.append(ContentIdea(**current_idea))
                    key_points = []
                current_idea = {"hook": line.split(":", 1)[-1].strip().replace("**", "").strip('"')}
            elif line.startswith("TOPIC:") or line.startswith("MAIN_TOPIC:"):
                current_idea["main_topic"] = line.split(":", 1)[-1].strip()
            elif line.startswith("KEY_POINTS:") or line.startswith("KEY POINTS:"):
                points_text = line.split(":", 1)[-1].strip()
                if points_text:
                    key_points = [p.strip() for p in points_text.split(",")]
            elif line.startswith("-") or line.startswith("•") or line.startswith("*"):
                point = line.strip("-•* ").strip()
                if point and len(point) > 5:
                    key_points.append(point)
            elif line.startswith("CTA:") or line.startswith("CALL"):
                current_idea["call_to_action"] = line.split(":", 1)[-1].strip()
            elif line.startswith("TYPE:"):
                current_idea["content_type"] = line.split(":", 1)[-1].strip().lower()
            elif line.startswith("ENGAGEMENT:"):
                engagement = line.split(":", 1)[-1].strip().lower()
                current_idea["estimated_engagement"] = engagement if engagement in ["high", "medium", "low"] else "medium"
        
        # Add last idea
        if current_idea.get("hook") and current_idea.get("main_topic"):
            current_idea["key_points"] = key_points if key_points else ["Key insight 1", "Key insight 2", "Key insight 3"]
            if "call_to_action" not in current_idea:
                current_idea["call_to_action"] = "What's your take? Share in the comments!"
            if "content_type" not in current_idea:
                current_idea["content_type"] = "tips"
            if "estimated_engagement" not in current_idea:
                current_idea["estimated_engagement"] = "medium"
            ideas.append(ContentIdea(**current_idea))
        
        # Extract daily suggestion
        daily = "Share a recent win or learning from your work this week."
        for line in content.split("\n"):
            if "DAILY" in line.upper():
                daily = line.split(":", 1)[-1].strip() if ":" in line else line
                break
        
        return GenerateIdeasResponse(
            success=True,
            ideas=ideas[:request.num_ideas],
            daily_suggestion=daily
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-post", response_model=GeneratePostResponse)
async def generate_linkedin_post(request: GeneratePostRequest):
    """
    Generate a full, publish-ready LinkedIn post.
    
    Creates engaging long-form content with:
    - Attention-grabbing hook
    - Structured body with storytelling elements
    - Strategic hashtags
    - Optimal posting time suggestions
    - Optional variations for A/B testing
    """
    settings = get_settings()
    api_key = settings.perplexity_api_key
    
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Perplexity API key not configured."
        )
    
    # Determine what to write about
    if request.content_idea:
        topic = f"Hook: {request.content_idea.hook}\nTopic: {request.content_idea.main_topic}\nKey Points: {', '.join(request.content_idea.key_points)}"
    elif request.topic:
        topic = request.topic
    else:
        topic = f"A thought leadership post about {request.profile.industry}"
    
    style_instructions = {
        "storytelling": "Use a personal story or anecdote. Start with a hook, build tension, deliver insight.",
        "listicle": "Use numbered points or bullet format. Make it scannable and actionable.",
        "question": "Start with a thought-provoking question. Build curiosity throughout.",
        "hot_take": "Lead with a controversial or unexpected opinion. Back it up with reasoning.",
        "educational": "Teach something valuable. Use clear structure: problem, solution, examples."
    }
    
    system_prompt = f"""You are a viral LinkedIn content creator who has generated millions of impressions.
You write posts that are authentic, valuable, and highly engaging.
You understand LinkedIn's algorithm favors: storytelling, line breaks, hooks, and genuine insights.
Style: {style_instructions.get(request.style, style_instructions['storytelling'])}
{'Use emojis strategically to add visual interest.' if request.include_emoji else 'Avoid emojis.'}"""

    query = f"""Write a LinkedIn post for:

Profile:
- Name: {request.profile.name}
- Industry: {request.profile.industry}
- Tagline: {request.profile.tagline or 'Not provided'}
- Values: {", ".join(request.profile.values) if request.profile.values else 'Not specified'}

Topic/Idea: {topic}

Goal: {request.goals.goal_type}
Tone: {request.goals.tone}
Max Length: {request.max_length} characters

Create a complete, publish-ready LinkedIn post that:
1. Starts with a compelling hook (first 2 lines are crucial)
2. Uses short paragraphs and line breaks for readability
3. Includes a clear call-to-action
4. Is authentic and provides genuine value

Also provide:
- HASHTAGS: [5 relevant hashtags]
- BEST_TIME: [Best time to post this content]
- EDITING_TIP: [One suggestion to improve engagement]
{f'- VARIATION: [An alternative opening for A/B testing]' if request.generate_variations else ''}"""

    try:
        result = await perplexity_search(query, system_prompt, api_key)
        content = result["content"]
        
        # Parse the response
        post_content = ""
        hashtags = []
        best_time = "Tuesday-Thursday, 8-10 AM or 5-7 PM"
        editing_tips = []
        variations = []
        
        # Split into sections
        sections = content.split("\n\n")
        post_parts = []
        
        for section in sections:
            section = section.strip()
            if section.startswith("HASHTAGS:") or section.startswith("**HASHTAGS"):
                tags = section.split(":", 1)[-1].strip()
                hashtags = [t.strip().replace("#", "") for t in tags.replace(",", " ").split() if t.strip()]
            elif section.startswith("BEST_TIME:") or section.startswith("**BEST"):
                best_time = section.split(":", 1)[-1].strip()
            elif section.startswith("EDITING_TIP:") or section.startswith("**EDITING"):
                editing_tips.append(section.split(":", 1)[-1].strip())
            elif section.startswith("VARIATION:") or section.startswith("**VARIATION"):
                variations.append(section.split(":", 1)[-1].strip())
            elif not any(section.startswith(x) for x in ["Here's", "Here is", "I've created", "Below"]):
                # This is likely post content
                post_parts.append(section)
        
        post_content = "\n\n".join(post_parts).strip()
        
        # Clean up post content
        post_content = post_content.replace("**", "").replace("```", "").strip()
        
        # Ensure we have hashtags
        if not hashtags:
            hashtags = [request.profile.industry.replace(" ", ""), "LinkedIn", "CareerGrowth", "Leadership", "Insights"]
        
        # Extract hook (first meaningful line)
        hook = post_content.split("\n")[0].strip() if post_content else "Check out this insight..."
        
        # Default editing tip
        if not editing_tips:
            editing_tips = ["Add a specific metric or number to increase credibility"]
        
        return GeneratePostResponse(
            success=True,
            post=GeneratedPost(
                content=post_content[:request.max_length] if len(post_content) > request.max_length else post_content,
                hook=hook,
                hashtags=hashtags[:7],
                estimated_reach="1,000-5,000 impressions (varies by network size)",
                best_posting_time=best_time,
                variations=variations
            ),
            editing_suggestions=editing_tips
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily-plan", response_model=DailyContentPlanResponse)
async def generate_daily_content_plan(request: DailyContentPlanRequest):
    """
    Generate a multi-day LinkedIn content plan.
    
    Creates a strategic content calendar with:
    - Daily topics and themes
    - Content type variety
    - Hooks for each day
    - Optimal posting times
    """
    settings = get_settings()
    api_key = settings.perplexity_api_key
    
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Perplexity API key not configured."
        )
    
    system_prompt = """You are a LinkedIn content strategist who creates viral content calendars.
You understand content variety, audience fatigue, and engagement patterns.
Create a strategic plan that balances different content types for maximum impact."""

    query = f"""Create a {request.days}-day LinkedIn content plan for:

Profile:
- Name: {request.profile.name}
- Industry: {request.profile.industry}
- Values: {", ".join(request.profile.values) if request.profile.values else 'Not specified'}

Goal: {request.goals.goal_type}
Tone: {request.goals.tone}

For each day provide:
- DAY: [number]
- TOPIC: [specific topic]
- TYPE: [story/tips/opinion/question/news_commentary/celebration]
- HOOK: [attention-grabbing first line]
- BEST_TIME: [optimal posting time]

Also identify 3 THEMES that tie the content together."""

    try:
        result = await perplexity_search(query, system_prompt, api_key)
        content = result["content"]
        
        # Parse daily plan
        plan = []
        current_day = {}
        themes = []
        
        from datetime import datetime, timedelta
        today = datetime.now()
        
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("DAY:") or (line.startswith("**Day") or line.startswith("Day ")):
                if current_day.get("topic"):
                    day_num = current_day.get("day", len(plan) + 1)
                    current_day["date"] = (today + timedelta(days=day_num-1)).strftime("%Y-%m-%d")
                    if "best_time" not in current_day:
                        current_day["best_time"] = "9:00 AM"
                    plan.append(DailyContentItem(**current_day))
                day_num = line.split(":")[-1].strip().replace("**", "").replace("Day", "").strip()
                try:
                    current_day = {"day": int(day_num.split()[0])}
                except:
                    current_day = {"day": len(plan) + 1}
            elif line.startswith("TOPIC:"):
                current_day["topic"] = line.split(":", 1)[-1].strip()
            elif line.startswith("TYPE:"):
                current_day["content_type"] = line.split(":", 1)[-1].strip().lower()
            elif line.startswith("HOOK:"):
                current_day["hook"] = line.split(":", 1)[-1].strip().strip('"')
            elif line.startswith("BEST_TIME:") or line.startswith("TIME:"):
                current_day["best_time"] = line.split(":", 1)[-1].strip()
            elif "THEME" in line.upper():
                theme = line.split(":", 1)[-1].strip() if ":" in line else ""
                if theme and len(theme) > 5:
                    themes.append(theme)
        
        # Add last day
        if current_day.get("topic"):
            day_num = current_day.get("day", len(plan) + 1)
            current_day["date"] = (today + timedelta(days=day_num-1)).strftime("%Y-%m-%d")
            if "content_type" not in current_day:
                current_day["content_type"] = "tips"
            if "hook" not in current_day:
                current_day["hook"] = f"Here's what I learned about {current_day['topic']}..."
            if "best_time" not in current_day:
                current_day["best_time"] = "9:00 AM"
            plan.append(DailyContentItem(**current_day))
        
        # Default themes if none found
        if not themes:
            themes = [
                f"{request.profile.industry} insights and trends",
                "Personal growth and lessons learned",
                "Value-driven content for your audience"
            ]
        
        return DailyContentPlanResponse(
            success=True,
            plan=plan[:request.days],
            themes=themes[:5]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def content_creator_health():
    """Check content creator module health"""
    settings = get_settings()
    perplexity_configured = bool(settings.perplexity_api_key)
    
    return {
        "status": "ok" if perplexity_configured else "degraded",
        "perplexity_api": "configured" if perplexity_configured else "missing",
        "features": {
            "discover_topics": perplexity_configured,
            "generate_ideas": perplexity_configured,
            "generate_posts": perplexity_configured,
            "daily_plans": perplexity_configured
        }
    }
