"""
Website Scraper Module
Extracts brand information from websites using BeautifulSoup.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, Any, Optional, List
import re

from app.scraping.logo_extractor import find_and_download_logo
from app.scraping.color_extractor import extract_colors_from_image


# Common user agent to avoid blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Timeout for requests
TIMEOUT = 15


async def scrape_brand_data(url: str) -> Dict[str, Any]:
    """
    Main function to scrape brand data from a website.
    
    Args:
        url: The website URL to scrape
        
    Returns:
        Dict containing company_name, tagline, logo, colors, website
    """
    # Ensure URL has scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Fetch the webpage
    html = fetch_webpage(url)
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract company information
    company_info = extract_company_info(soup, url)
    meta_info = extract_meta_tags(soup)
    
    # Get company name (prioritize meta, then title)
    company_name = (
        meta_info.get('og:site_name') or
        meta_info.get('application-name') or
        company_info.get('title') or
        extract_domain_name(url)
    )
    
    # Get tagline
    tagline = (
        meta_info.get('description') or
        company_info.get('tagline') or
        meta_info.get('og:description')
    )
    # Truncate tagline if too long
    if tagline and len(tagline) > 200:
        tagline = tagline[:197] + "..."
    
    # Extract logo
    logo_result = await find_and_download_logo(soup, url)
    
    # Extract colors from logo if available
    colors = []
    if logo_result and logo_result.get('image_data'):
        colors = extract_colors_from_image(logo_result['image_data'])
    
    # Build response
    from app.database.neo4j_client import neo4j_client
    
    brand_data = {
        "company_name": clean_text(company_name),
        "tagline": clean_text(tagline) if tagline else None,
        "website": url,
        "logo": {
            "url": logo_result.get('url') if logo_result else None,
            "quality_score": logo_result.get('quality_score') if logo_result else None,
            "needs_enhancement": (logo_result.get('quality_score', 0) < 0.7) if logo_result else True
        } if logo_result else None,
        "colors": colors
    }
    
    # Save to Neo4j and get ID
    brand_id = neo4j_client.create_brand(brand_data)
    brand_data["id"] = brand_id
    
    return brand_data


def fetch_webpage(url: str) -> str:
    """
    Fetch HTML content from a URL.
    
    Args:
        url: The URL to fetch
        
    Returns:
        HTML content as string
        
    Raises:
        Exception: If request fails
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        raise Exception(f"Timeout while fetching {url}")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Could not connect to {url}")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"HTTP error {e.response.status_code} for {url}")
    except Exception as e:
        raise Exception(f"Failed to fetch {url}: {str(e)}")


def extract_company_info(soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
    """
    Extract company information from HTML structure.
    
    Args:
        soup: BeautifulSoup parsed HTML
        base_url: Base URL for resolving relative paths
        
    Returns:
        Dict with title, tagline, and other extracted info
    """
    info = {}
    
    # Get title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text().strip()
        # Clean common title suffixes
        title = re.split(r'\s*[|\-–—]\s*', title)[0].strip()
        info['title'] = title
    
    # Try to find tagline from h1 or prominent text
    h1_tag = soup.find('h1')
    if h1_tag:
        h1_text = h1_tag.get_text().strip()
        # If h1 is different from title, might be a tagline
        if h1_text and info.get('title') and h1_text.lower() != info['title'].lower():
            if len(h1_text) < 150:  # Reasonable tagline length
                info['tagline'] = h1_text
    
    # Try hero section for tagline
    hero_selectors = ['.hero', '#hero', '[class*="hero"]', '[class*="banner"]', 'header']
    for selector in hero_selectors:
        hero = soup.select_one(selector)
        if hero:
            p_tag = hero.find('p')
            if p_tag:
                text = p_tag.get_text().strip()
                if text and len(text) < 200 and not info.get('tagline'):
                    info['tagline'] = text
                    break
    
    return info


def extract_meta_tags(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extract useful meta tags from HTML.
    
    Args:
        soup: BeautifulSoup parsed HTML
        
    Returns:
        Dict of meta tag names/properties to their content
    """
    meta_info = {}
    
    # Standard meta tags
    for meta in soup.find_all('meta'):
        name = meta.get('name') or meta.get('property')
        content = meta.get('content')
        
        if name and content:
            meta_info[name.lower()] = content
    
    return meta_info


def extract_domain_name(url: str) -> str:
    """
    Extract a readable company name from URL domain.
    
    Args:
        url: The website URL
        
    Returns:
        Formatted domain name
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Get just the name part (remove TLD)
    name = domain.split('.')[0]
    
    # Capitalize
    return name.title()


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean and normalize text content"""
    if not text:
        return None
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove common unwanted characters
    text = text.strip()
    
    return text if text else None


def extract_brand_data_sync(url: str) -> Dict[str, Any]:
    """
    Synchronous version of brand data extraction.
    Extracts basic brand info without saving to database.
    
    Args:
        url: The website URL to scrape
        
    Returns:
        Dict containing brand_name, tagline, logo_url, colors, style_keywords
    """
    # Ensure URL has scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Fetch the webpage
        html = fetch_webpage(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract company information
        company_info = extract_company_info(soup, url)
        meta_info = extract_meta_tags(soup)
        
        # Get company name
        company_name = (
            meta_info.get('og:site_name') or
            meta_info.get('application-name') or
            company_info.get('title') or
            extract_domain_name(url)
        )
        
        # Get tagline
        tagline = (
            meta_info.get('description') or
            company_info.get('tagline') or
            meta_info.get('og:description')
        )
        if tagline and len(tagline) > 200:
            tagline = tagline[:197] + "..."
        
        # Find logo URL (sync version)
        logo_url = None
        
        # Try common logo selectors
        logo_selectors = [
            'img[class*="logo"]',
            'img[id*="logo"]',
            'img[alt*="logo"]',
            '.logo img',
            '#logo img',
            'header img:first-child',
            'a[class*="logo"] img',
            'img[src*="logo"]'
        ]
        
        for selector in logo_selectors:
            logo_elem = soup.select_one(selector)
            if logo_elem and logo_elem.get('src'):
                logo_url = urljoin(url, logo_elem['src'])
                break
        
        # Detect style from page content
        style_keywords = detect_style_from_content(soup, meta_info)
        detected_style = determine_overall_style(style_keywords)
        
        # Try to determine industry
        industry = detect_industry(soup, meta_info, company_name)
        
        return {
            "brand_name": clean_text(company_name),
            "tagline": clean_text(tagline) if tagline else None,
            "logo_url": logo_url,
            "website_url": url,
            "style_keywords": style_keywords,
            "detected_style": detected_style,
            "industry": industry
        }
        
    except Exception as e:
        # Return minimal data on error
        return {
            "brand_name": extract_domain_name(url),
            "tagline": None,
            "logo_url": None,
            "website_url": url,
            "style_keywords": ["professional", "modern"],
            "detected_style": "professional",
            "industry": "general",
            "error": str(e)
        }


def detect_style_from_content(soup: BeautifulSoup, meta_info: Dict) -> List[str]:
    """Detect visual style keywords from website content"""
    keywords = []
    
    # Get all text content
    text_content = soup.get_text().lower()
    
    # Style keyword patterns
    style_patterns = {
        'minimal': ['minimal', 'simple', 'clean', 'sleek'],
        'bold': ['bold', 'vibrant', 'dynamic', 'powerful'],
        'elegant': ['elegant', 'luxury', 'premium', 'sophisticated'],
        'playful': ['fun', 'playful', 'creative', 'colorful'],
        'professional': ['professional', 'trusted', 'reliable', 'expert'],
        'modern': ['modern', 'innovative', 'cutting-edge', 'digital'],
        'natural': ['natural', 'organic', 'sustainable', 'eco'],
        'vintage': ['vintage', 'classic', 'heritage', 'traditional']
    }
    
    for style, patterns in style_patterns.items():
        for pattern in patterns:
            if pattern in text_content:
                keywords.append(style)
                break
    
    # Default keywords if none found
    if not keywords:
        keywords = ['professional', 'modern']
    
    return list(set(keywords))[:5]  # Max 5 keywords


def determine_overall_style(keywords: List[str]) -> str:
    """Determine primary style from keywords"""
    if not keywords:
        return "professional"
    
    # Priority order
    priority = ['minimal', 'elegant', 'bold', 'playful', 'modern', 'professional']
    
    for style in priority:
        if style in keywords:
            return style
    
    return keywords[0]


def detect_industry(soup: BeautifulSoup, meta_info: Dict, company_name: str) -> str:
    """Detect industry from website content"""
    text_content = soup.get_text().lower()
    
    industry_patterns = {
        'technology': ['software', 'tech', 'digital', 'app', 'platform', 'saas'],
        'ecommerce': ['shop', 'store', 'buy', 'cart', 'product', 'shipping'],
        'finance': ['bank', 'finance', 'investment', 'money', 'insurance'],
        'healthcare': ['health', 'medical', 'doctor', 'patient', 'care'],
        'food': ['food', 'restaurant', 'menu', 'recipe', 'eat', 'drink'],
        'fashion': ['fashion', 'clothing', 'wear', 'style', 'outfit'],
        'education': ['learn', 'course', 'education', 'student', 'training'],
        'travel': ['travel', 'hotel', 'flight', 'booking', 'destination']
    }
    
    for industry, patterns in industry_patterns.items():
        matches = sum(1 for p in patterns if p in text_content)
        if matches >= 2:
            return industry
    
    return "general"
