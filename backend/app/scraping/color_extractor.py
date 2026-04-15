"""
Color Extractor Module
Extracts dominant colors from images using ColorThief.
"""
from colorthief import ColorThief
from io import BytesIO
from typing import List, Dict
from PIL import Image


# Color name mapping for common colors
COLOR_NAMES = {
    # Reds
    (255, 0, 0): "Red",
    (220, 20, 60): "Crimson",
    (178, 34, 34): "Firebrick",
    (139, 0, 0): "Dark Red",
    # Oranges
    (255, 165, 0): "Orange",
    (255, 140, 0): "Dark Orange",
    (255, 127, 80): "Coral",
    # Yellows
    (255, 255, 0): "Yellow",
    (255, 215, 0): "Gold",
    (255, 255, 224): "Light Yellow",
    # Greens
    (0, 128, 0): "Green",
    (0, 255, 0): "Lime",
    (34, 139, 34): "Forest Green",
    (144, 238, 144): "Light Green",
    (0, 100, 0): "Dark Green",
    # Blues
    (0, 0, 255): "Blue",
    (0, 0, 139): "Dark Blue",
    (30, 144, 255): "Dodger Blue",
    (135, 206, 235): "Sky Blue",
    (0, 191, 255): "Deep Sky Blue",
    (70, 130, 180): "Steel Blue",
    # Purples
    (128, 0, 128): "Purple",
    (148, 0, 211): "Dark Violet",
    (238, 130, 238): "Violet",
    (255, 0, 255): "Magenta",
    # Browns
    (165, 42, 42): "Brown",
    (139, 69, 19): "Saddle Brown",
    (210, 180, 140): "Tan",
    # Grays
    (128, 128, 128): "Gray",
    (169, 169, 169): "Dark Gray",
    (211, 211, 211): "Light Gray",
    (192, 192, 192): "Silver",
    # Black & White
    (0, 0, 0): "Black",
    (255, 255, 255): "White",
    (245, 245, 245): "White Smoke",
    # Teals & Cyans
    (0, 128, 128): "Teal",
    (0, 255, 255): "Cyan",
    (64, 224, 208): "Turquoise",
    # Pinks
    (255, 192, 203): "Pink",
    (255, 105, 180): "Hot Pink",
    (255, 182, 193): "Light Pink",
}


def extract_colors_from_image(image_data: bytes, color_count: int = 5) -> List[Dict[str, str]]:
    """
    Extract dominant colors from an image.
    
    Args:
        image_data: Raw image bytes
        color_count: Number of colors to extract (default 5)
        
    Returns:
        List of dicts with 'hex' and 'name' keys
    """
    try:
        # ColorThief needs a file-like object
        image_file = BytesIO(image_data)
        
        # Ensure image is in a format ColorThief can read
        img = Image.open(image_file)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Convert to RGB for ColorThief
            img = img.convert('RGB')
            image_file = BytesIO()
            img.save(image_file, 'PNG')
            image_file.seek(0)
        else:
            image_file.seek(0)
        
        color_thief = ColorThief(image_file)
        
        # Get color palette
        palette = color_thief.get_palette(color_count=color_count, quality=1)
        
        colors = []
        for rgb in palette:
            hex_color = rgb_to_hex(rgb)
            color_name = get_color_name(rgb)
            colors.append({
                "hex": hex_color,
                "name": color_name
            })
        
        return colors
        
    except Exception as e:
        print(f"Error extracting colors: {e}")
        return []


def rgb_to_hex(rgb: tuple) -> str:
    """
    Convert RGB tuple to hex string.
    
    Args:
        rgb: Tuple of (R, G, B) values 0-255
        
    Returns:
        Hex color string like "#FF5733"
    """
    return "#{:02X}{:02X}{:02X}".format(rgb[0], rgb[1], rgb[2])


def hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert hex color string to RGB tuple.
    
    Args:
        hex_color: Hex string like "#FF5733" or "FF5733"
        
    Returns:
        Tuple of (R, G, B) values
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_color_name(rgb: tuple) -> str:
    """
    Get a human-readable name for a color.
    
    Uses nearest neighbor matching against known colors.
    
    Args:
        rgb: Tuple of (R, G, B) values
        
    Returns:
        Color name string
    """
    min_distance = float('inf')
    closest_name = "Unknown"
    
    for known_rgb, name in COLOR_NAMES.items():
        # Calculate Euclidean distance in RGB space
        distance = sum((a - b) ** 2 for a, b in zip(rgb, known_rgb)) ** 0.5
        
        if distance < min_distance:
            min_distance = distance
            closest_name = name
    
    # If the distance is too large, generate a descriptive name
    if min_distance > 100:
        r, g, b = rgb
        
        # Determine brightness
        brightness = (r + g + b) / 3
        if brightness > 200:
            prefix = "Light"
        elif brightness < 60:
            prefix = "Dark"
        else:
            prefix = ""
        
        # Determine dominant channel
        if r > g and r > b:
            base = "Red" if r > 150 else "Brown"
        elif g > r and g > b:
            base = "Green"
        elif b > r and b > g:
            base = "Blue"
        elif r > 200 and g > 200:
            base = "Yellow"
        elif r > 200 and b > 200:
            base = "Pink"
        elif g > 200 and b > 200:
            base = "Cyan"
        else:
            base = "Gray"
        
        closest_name = f"{prefix} {base}".strip()
    
    return closest_name


def compare_colors(color1: str, color2: str) -> float:
    """
    Compare two colors and return a similarity score.
    
    Args:
        color1: First hex color
        color2: Second hex color
        
    Returns:
        Similarity score from 0.0 to 1.0 (1.0 = identical)
    """
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    # Calculate distance (max distance is ~441 for black to white)
    distance = sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
    max_distance = 441.67  # sqrt(255^2 * 3)
    
    similarity = 1 - (distance / max_distance)
    return round(similarity, 2)


def find_closest_brand_color(target_hex: str, brand_colors: List[str]) -> tuple:
    """
    Find the closest matching brand color for a given color.
    
    Args:
        target_hex: The color to match
        brand_colors: List of brand hex colors
        
    Returns:
        Tuple of (closest_hex, similarity_score)
    """
    best_match = None
    best_score = 0
    
    for brand_color in brand_colors:
        score = compare_colors(target_hex, brand_color)
        if score > best_score:
            best_score = score
            best_match = brand_color
    
    return (best_match, best_score)


def extract_colors_from_url(url: str, color_count: int = 5) -> List[Dict[str, str]]:
    """
    Extract dominant colors from an image URL or webpage.
    
    Args:
        url: Image URL or webpage URL
        color_count: Number of colors to extract
        
    Returns:
        List of dicts with 'hex' and 'name' keys
    """
    import requests
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        
        # If it's an image, extract colors directly
        if 'image' in content_type:
            return extract_colors_from_image(response.content, color_count)
        
        # If it's HTML, try to find logo and extract colors from it
        if 'html' in content_type:
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find logo image
            logo_selectors = [
                'img[class*="logo"]',
                'img[id*="logo"]',
                '.logo img',
                'header img:first-child'
            ]
            
            for selector in logo_selectors:
                logo = soup.select_one(selector)
                if logo and logo.get('src'):
                    logo_url = urljoin(url, logo['src'])
                    
                    # Fetch logo and extract colors
                    logo_response = requests.get(logo_url, headers=headers, timeout=10)
                    if logo_response.ok:
                        return extract_colors_from_image(logo_response.content, color_count)
        
        return []
        
    except Exception as e:
        print(f"Error extracting colors from URL: {e}")
        return []
