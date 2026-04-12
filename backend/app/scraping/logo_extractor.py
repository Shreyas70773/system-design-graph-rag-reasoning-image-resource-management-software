"""
Logo Extractor Module
Finds and downloads logo images from websites.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, Any, Optional, List
from io import BytesIO
from PIL import Image
import re


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def find_and_download_logo(soup: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
    """
    Find and download the logo from a website.
    
    Search strategy:
    1. Look for <img> tags with "logo" in class, id, or alt
    2. Look for <link rel="icon"> or <link rel="apple-touch-icon">
    3. Look for Open Graph image
    4. Try common logo paths
    
    Args:
        soup: BeautifulSoup parsed HTML
        base_url: Base URL for resolving relative paths
        
    Returns:
        Dict with url, image_data, quality_score, or None if not found
    """
    logo_url = None
    
    # Strategy 1: Find img tags with "logo" identifier
    logo_url = find_logo_in_images(soup, base_url)
    
    # Strategy 2: Check for high-res favicon/apple-touch-icon
    if not logo_url:
        logo_url = find_favicon(soup, base_url)
    
    # Strategy 3: Open Graph image (og:image)
    if not logo_url:
        logo_url = find_og_image(soup, base_url)
    
    # Strategy 4: Try common paths
    if not logo_url:
        logo_url = await try_common_logo_paths(base_url)
    
    # Download and assess the logo
    if logo_url:
        image_data = download_image(logo_url)
        if image_data:
            quality_score = calculate_logo_quality(image_data)
            return {
                "url": logo_url,
                "image_data": image_data,
                "quality_score": quality_score
            }
    
    return None


def find_logo_in_images(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """
    Find logo URL in <img> tags.
    
    Looks for images with "logo" in their class, id, alt, or src.
    """
    logo_patterns = ['logo', 'brand', 'header-img', 'site-logo']
    
    for img in soup.find_all('img'):
        # Check various attributes for logo indicators
        img_class = ' '.join(img.get('class', []))
        img_id = img.get('id', '')
        img_alt = img.get('alt', '')
        img_src = img.get('src', '')
        
        # Combine all attributes for searching
        combined = f"{img_class} {img_id} {img_alt} {img_src}".lower()
        
        for pattern in logo_patterns:
            if pattern in combined:
                src = img.get('src') or img.get('data-src')
                if src:
                    return urljoin(base_url, src)
    
    # Also check in header specifically
    header = soup.find('header') or soup.find(class_=re.compile(r'header', re.I))
    if header:
        first_img = header.find('img')
        if first_img:
            src = first_img.get('src') or first_img.get('data-src')
            if src:
                return urljoin(base_url, src)
    
    return None


def find_favicon(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """
    Find high-resolution favicon or apple-touch-icon.
    """
    # Look for apple-touch-icon (typically higher resolution)
    for link in soup.find_all('link', rel=re.compile(r'apple-touch-icon', re.I)):
        href = link.get('href')
        if href:
            return urljoin(base_url, href)
    
    # Look for larger favicons
    for link in soup.find_all('link', rel='icon'):
        href = link.get('href')
        sizes = link.get('sizes', '')
        # Prefer larger icons
        if href and ('192' in sizes or '180' in sizes or '152' in sizes):
            return urljoin(base_url, href)
    
    # Fallback to any icon
    for link in soup.find_all('link', rel='icon'):
        href = link.get('href')
        if href and not href.endswith('.ico'):  # Skip tiny .ico files
            return urljoin(base_url, href)
    
    return None


def find_og_image(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """
    Find Open Graph image meta tag.
    """
    og_image = soup.find('meta', property='og:image')
    if og_image:
        content = og_image.get('content')
        if content:
            return urljoin(base_url, content)
    
    # Twitter card image as fallback
    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
    if twitter_image:
        content = twitter_image.get('content')
        if content:
            return urljoin(base_url, content)
    
    return None


async def try_common_logo_paths(base_url: str) -> Optional[str]:
    """
    Try common paths where logos are often located.
    """
    common_paths = [
        '/logo.png',
        '/logo.svg',
        '/img/logo.png',
        '/images/logo.png',
        '/assets/logo.png',
        '/assets/images/logo.png',
        '/static/logo.png',
        '/wp-content/uploads/logo.png',
    ]
    
    for path in common_paths:
        url = urljoin(base_url, path)
        try:
            response = requests.head(url, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                return url
        except:
            continue
    
    return None


def download_image(url: str) -> Optional[bytes]:
    """
    Download an image from URL.
    
    Args:
        url: Image URL
        
    Returns:
        Image bytes or None if failed
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # Verify it's actually an image
        content_type = response.headers.get('content-type', '')
        if 'image' in content_type or url.endswith(('.png', '.jpg', '.jpeg', '.svg', '.webp')):
            return response.content
        
        return None
    except Exception as e:
        print(f"Failed to download image {url}: {e}")
        return None


def calculate_logo_quality(image_data: bytes) -> float:
    """
    Calculate a quality score for the logo image.
    
    Checks:
    - Resolution (min 200x200 for good quality)
    - Aspect ratio (logos are typically square-ish or wide)
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Quality score from 0.0 to 1.0
    """
    try:
        img = Image.open(BytesIO(image_data))
        width, height = img.size
        
        # Resolution score (target: 200x200 minimum)
        min_dimension = min(width, height)
        if min_dimension >= 200:
            resolution_score = 1.0
        elif min_dimension >= 100:
            resolution_score = min_dimension / 200
        else:
            resolution_score = min_dimension / 200 * 0.5
        
        # Size score - larger is better up to a point
        total_pixels = width * height
        if total_pixels >= 40000:  # 200x200
            size_score = 1.0
        elif total_pixels >= 10000:  # 100x100
            size_score = 0.7
        else:
            size_score = 0.4
        
        # Combined score
        quality_score = (resolution_score * 0.6 + size_score * 0.4)
        
        return round(min(quality_score, 1.0), 2)
        
    except Exception as e:
        print(f"Error calculating logo quality: {e}")
        return 0.3  # Default low score for unreadable images
