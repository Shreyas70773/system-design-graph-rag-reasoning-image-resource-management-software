"""
Product URL Scraper Module
Scrapes products from product pages/catalogs.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re
from urllib.parse import urljoin


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def scrape_product_page(url: str) -> List[Dict[str, Any]]:
    """
    Scrape products from a product page or catalog.
    
    Looks for common product card patterns in HTML.
    
    Args:
        url: URL of the product page
        
    Returns:
        List of product dictionaries
    """
    # Fetch the page
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = []
    
    # Strategy 1: Look for schema.org Product markup
    products = extract_schema_products(soup)
    if products:
        return products
    
    # Strategy 2: Look for common product card patterns
    products = extract_product_cards(soup, url)
    if products:
        return products
    
    # Strategy 3: Look for product-like elements
    products = extract_generic_products(soup, url)
    
    return products


def extract_schema_products(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extract products from schema.org JSON-LD markup.
    """
    products = []
    
    # Look for JSON-LD scripts
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            import json
            data = json.loads(script.string)
            
            # Handle single product or array
            items = data if isinstance(data, list) else [data]
            
            for item in items:
                if item.get('@type') == 'Product':
                    product = {
                        "name": item.get('name'),
                        "price": None,
                        "description": item.get('description'),
                        "image_url": item.get('image'),
                        "category": None
                    }
                    
                    # Extract price
                    offers = item.get('offers', {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    
                    if offers.get('price'):
                        currency = offers.get('priceCurrency', '$')
                        product['price'] = f"{currency}{offers['price']}"
                    
                    products.append(product)
        except:
            continue
    
    return products


def extract_product_cards(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    """
    Extract products from common product card HTML patterns.
    """
    products = []
    
    # Common product card class patterns
    card_selectors = [
        '[class*="product-card"]',
        '[class*="product-item"]',
        '[class*="product_card"]',
        '[class*="productCard"]',
        '.product',
        '.item',
        '[data-product]',
        '[itemtype*="Product"]'
    ]
    
    cards = []
    for selector in card_selectors:
        cards = soup.select(selector)
        if len(cards) >= 2:  # Found multiple product cards
            break
    
    for card in cards[:20]:  # Limit to first 20
        product = extract_product_from_element(card, base_url)
        if product and product.get('name'):
            products.append(product)
    
    return products


def extract_product_from_element(element, base_url: str) -> Dict[str, Any]:
    """
    Extract product data from a single HTML element.
    """
    product = {
        "name": None,
        "price": None,
        "description": None,
        "image_url": None,
        "category": None
    }
    
    # Extract name
    name_selectors = [
        '[class*="product-name"]',
        '[class*="product-title"]',
        '[class*="item-name"]',
        'h2', 'h3', 'h4',
        '[class*="name"]',
        '[class*="title"]'
    ]
    
    for selector in name_selectors:
        name_elem = element.select_one(selector)
        if name_elem:
            product['name'] = name_elem.get_text().strip()
            if product['name']:
                break
    
    # Extract price
    price_selectors = [
        '[class*="price"]',
        '[class*="cost"]',
        '[data-price]',
        '.price'
    ]
    
    for selector in price_selectors:
        price_elem = element.select_one(selector)
        if price_elem:
            price_text = price_elem.get_text().strip()
            # Look for price pattern
            price_match = re.search(r'[\$£€]\s*[\d,]+\.?\d*', price_text)
            if price_match:
                product['price'] = price_match.group()
                break
    
    # Extract image
    img = element.find('img')
    if img:
        src = img.get('src') or img.get('data-src')
        if src:
            product['image_url'] = urljoin(base_url, src)
    
    # Extract description
    desc_selectors = [
        '[class*="description"]',
        '[class*="desc"]',
        'p'
    ]
    
    for selector in desc_selectors:
        desc_elem = element.select_one(selector)
        if desc_elem and desc_elem != element:
            desc_text = desc_elem.get_text().strip()
            if desc_text and len(desc_text) > 10:
                product['description'] = desc_text[:200]
                break
    
    return product


def extract_generic_products(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    """
    Fallback: try to find any product-like content.
    """
    products = []
    
    # Look for any element with price nearby
    price_elements = soup.find_all(string=re.compile(r'[\$£€]\s*\d+'))
    
    for price_elem in price_elements[:10]:
        parent = price_elem.parent
        if parent:
            # Look for nearby heading or strong text for name
            container = parent.parent if parent.parent else parent
            
            name = None
            for tag in ['h1', 'h2', 'h3', 'h4', 'strong', 'b']:
                name_elem = container.find(tag)
                if name_elem:
                    name = name_elem.get_text().strip()
                    break
            
            if name:
                price_match = re.search(r'[\$£€]\s*[\d,]+\.?\d*', price_elem)
                products.append({
                    "name": name,
                    "price": price_match.group() if price_match else None,
                    "description": None,
                    "image_url": None,
                    "category": None
                })
    
    return products
