"""
Smart Product URL Scraper Module
Scrapes product pages and uses OpenAI to extract structured product data.
"""
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
import re
from urllib.parse import urljoin, urlparse
import json

from app.config import get_settings


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


async def scrape_product_url(url: str) -> Dict[str, Any]:
    """
    Scrape a single product page and use OpenAI to extract structured data.
    
    Args:
        url: URL of the product page
        
    Returns:
        Dictionary with title, summary, price, image_url, and other product details
    """
    # Fetch the page
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=HEADERS, follow_redirects=True)
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    
    # Extract raw content
    raw_data = extract_raw_content(soup, base_url, url)
    
    # Use OpenAI to extract structured product data
    product_data = await extract_with_openai(raw_data, url)
    
    # Add the scraped image if OpenAI didn't find one
    if not product_data.get('image_url') and raw_data.get('main_image'):
        product_data['image_url'] = raw_data['main_image']
    
    # Add source URL
    product_data['source_url'] = url
    
    return product_data


def extract_raw_content(soup: BeautifulSoup, base_url: str, page_url: str) -> Dict[str, Any]:
    """
    Extract raw text and images from the page for OpenAI processing.
    """
    # Remove script, style, nav, footer elements
    for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        element.decompose()
    
    # Get page title
    title = soup.title.string if soup.title else None
    
    # Extract main content text
    main_content = ""
    
    # Try to find main content area
    main_selectors = ['main', 'article', '[role="main"]', '.product', '#product', '.product-detail']
    for selector in main_selectors:
        main_elem = soup.select_one(selector)
        if main_elem:
            main_content = main_elem.get_text(separator=' ', strip=True)
            break
    
    # Fallback to body if no main content found
    if not main_content:
        body = soup.find('body')
        if body:
            main_content = body.get_text(separator=' ', strip=True)
    
    # Clean up text - remove excessive whitespace
    main_content = re.sub(r'\s+', ' ', main_content)[:8000]  # Limit to ~8000 chars
    
    # Extract images
    images = []
    img_selectors = [
        '.product-image img',
        '.product-gallery img',
        '[data-product-image]',
        '.main-image img',
        'img[src*="product"]',
        'img[alt*="product"]',
        'article img',
        '.content img',
        'img'
    ]
    
    seen_urls = set()
    for selector in img_selectors:
        for img in soup.select(selector)[:10]:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                full_url = urljoin(base_url, src)
                # Filter out tiny images and duplicates
                if full_url not in seen_urls and not is_tracking_pixel(full_url, img):
                    seen_urls.add(full_url)
                    images.append({
                        'url': full_url,
                        'alt': img.get('alt', ''),
                        'width': img.get('width'),
                        'height': img.get('height')
                    })
        if len(images) >= 5:
            break
    
    # Try to find the "main" product image
    main_image = None
    if images:
        # Prefer images with product-related classes or alt text
        for img in images:
            if 'product' in img['url'].lower() or 'product' in img.get('alt', '').lower():
                main_image = img['url']
                break
        if not main_image:
            main_image = images[0]['url']
    
    # Extract meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    description = meta_desc.get('content', '') if meta_desc else ''
    
    # Extract prices from page (common patterns)
    price_texts = []
    price_patterns = soup.find_all(string=re.compile(r'[\$£€]\s*\d+[\d,\.]*'))
    for p in price_patterns[:5]:
        price_texts.append(p.strip())
    
    # Look for structured data (JSON-LD)
    structured_data = None
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'Product':
                structured_data = data
                break
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') == 'Product':
                        structured_data = item
                        break
        except:
            continue
    
    return {
        'page_title': title,
        'meta_description': description,
        'main_content': main_content,
        'images': images,
        'main_image': main_image,
        'price_texts': price_texts,
        'structured_data': structured_data,
        'url': page_url
    }


def is_tracking_pixel(url: str, img_element) -> bool:
    """Check if an image is likely a tracking pixel, preloader, or placeholder."""
    url_lower = url.lower()
    
    # Check URL for common tracking/placeholder patterns
    exclude_patterns = [
        'tracking', 'pixel', 'analytics', 'beacon', '1x1', 'spacer',
        'loader', 'loading', 'preloader', 'spinner', 'placeholder',
        'blank', 'empty', 'transparent', 'grey', 'gray', 'skeleton',
        'lazy', 'lazyload', 'data:image', 'base64', 'svg+xml',
        'icon', 'logo', 'badge', 'banner', 'ad', 'promo',
        'social', 'facebook', 'twitter', 'instagram', 'pinterest',
        'share', 'wishlist', 'cart', 'checkout', 'payment',
        'gif', '.gif'  # Often used for loaders
    ]
    if any(pattern in url_lower for pattern in exclude_patterns):
        return True
    
    # Check alt text for placeholder indicators
    alt = (img_element.get('alt') or '').lower()
    placeholder_alts = ['loading', 'placeholder', 'spinner', 'loader', '']
    if alt in placeholder_alts:
        # Empty alt might be okay if image looks valid
        if alt == '' and any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            pass  # Allow
        elif alt != '':
            return True
    
    # Check class names for loader indicators
    classes = (img_element.get('class') or [])
    if isinstance(classes, list):
        classes = ' '.join(classes)
    classes = classes.lower()
    loader_classes = ['loader', 'loading', 'spinner', 'skeleton', 'placeholder', 'lazy']
    if any(cls in classes for cls in loader_classes):
        return True
    
    # Check dimensions
    width = img_element.get('width')
    height = img_element.get('height')
    try:
        if width and height:
            if int(width) <= 2 or int(height) <= 2:
                return True
    except ValueError:
        pass
    
    return False


async def extract_with_openai(raw_data: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Use OpenAI to extract structured product information from raw page data.
    Falls back to Groq if OpenAI key is not available.
    """
    settings = get_settings()
    
    # Prepare the content for the LLM
    content = f"""
Page URL: {url}
Page Title: {raw_data.get('page_title', 'N/A')}
Meta Description: {raw_data.get('meta_description', 'N/A')}

Main Content:
{raw_data.get('main_content', 'N/A')[:5000]}

Detected Prices: {', '.join(raw_data.get('price_texts', [])[:5]) or 'None found'}
"""

    # If structured data exists, include it
    if raw_data.get('structured_data'):
        sd = raw_data['structured_data']
        content += f"""
Structured Product Data Found:
- Name: {sd.get('name', 'N/A')}
- Description: {sd.get('description', 'N/A')[:500] if sd.get('description') else 'N/A'}
- Price: {sd.get('offers', {}).get('price', 'N/A') if isinstance(sd.get('offers'), dict) else 'N/A'}
"""

    prompt = f"""Extract product information from this webpage content. Return a JSON object with these fields:
- name: Product name/title
- summary: A brief 1-2 sentence summary of the product
- description: Longer description (2-3 sentences)
- price: Price if found (include currency symbol)
- price_range: Price range if applicable
- category: Product category/type
- key_features: Array of 3-5 key features or selling points

If a field cannot be determined, use null.

Webpage Content:
{content}

Respond with ONLY valid JSON, no other text."""

    # Try OpenAI first, then fall back to Groq
    if settings.openai_api_key:
        return await call_openai(prompt, settings.openai_api_key)
    elif settings.groq_api_key:
        return await call_groq(prompt, settings.groq_api_key)
    else:
        # Return basic extraction without AI
        return extract_basic(raw_data)


async def call_openai(prompt: str, api_key: str) -> Dict[str, Any]:
    """Call OpenAI API for product extraction."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a product data extraction assistant. Extract structured product information from web page content. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 1000
            }
        )
        response.raise_for_status()
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        # Parse JSON from response
        return parse_json_response(content)


async def call_groq(prompt: str, api_key: str) -> Dict[str, Any]:
    """Call Groq API for product extraction (fallback)."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a product data extraction assistant. Extract structured product information from web page content. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 1000
            }
        )
        response.raise_for_status()
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        return parse_json_response(content)


def parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    # Remove markdown code blocks if present
    content = content.strip()
    if content.startswith('```'):
        lines = content.split('\n')
        content = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        
        # Return empty result if parsing fails
        return {
            "name": None,
            "summary": None,
            "description": None,
            "price": None,
            "price_range": None,
            "category": None,
            "key_features": []
        }


def extract_basic(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Basic extraction without AI (fallback)."""
    structured = raw_data.get('structured_data', {})
    
    price = None
    if structured and structured.get('offers'):
        offers = structured['offers']
        if isinstance(offers, dict) and offers.get('price'):
            currency = offers.get('priceCurrency', '$')
            price = f"{currency}{offers['price']}"
    elif raw_data.get('price_texts'):
        price = raw_data['price_texts'][0]
    
    return {
        "name": structured.get('name') or raw_data.get('page_title'),
        "summary": raw_data.get('meta_description', '')[:200] or None,
        "description": structured.get('description', '')[:500] if structured else None,
        "price": price,
        "price_range": None,
        "category": None,
        "key_features": []
    }


async def scrape_multiple_products(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Scrape multiple product URLs.
    
    Args:
        urls: List of product page URLs
        
    Returns:
        List of product data dictionaries
    """
    results = []
    for url in urls[:10]:  # Limit to 10 products
        try:
            product = await scrape_product_url(url)
            results.append(product)
        except Exception as e:
            results.append({
                "source_url": url,
                "error": str(e)
            })
    return results
