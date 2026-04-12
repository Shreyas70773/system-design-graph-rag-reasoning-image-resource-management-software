"""
Image Quality Assessment Module
Checks logo resolution, blur, and overall quality.
"""
from PIL import Image
from io import BytesIO
import numpy as np
from typing import Dict, Any, List
import requests


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def check_logo_quality(logo_url: str) -> Dict[str, Any]:
    """
    Comprehensive quality check for a logo image.
    
    Args:
        logo_url: URL of the logo to check
        
    Returns:
        Dict with quality_score, resolution, is_blurry, format, recommendations
    """
    # Download the image
    response = requests.get(logo_url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    image_data = response.content
    
    # Open with PIL
    img = Image.open(BytesIO(image_data))
    
    # Get basic info
    width, height = img.size
    format_type = img.format or "Unknown"
    
    # Check resolution
    resolution_ok = check_resolution(img)
    resolution_score = calculate_resolution_score(width, height)
    
    # Check blur
    is_blurry, blur_variance = check_blur(img)
    blur_score = calculate_blur_score(blur_variance)
    
    # Calculate overall quality score
    quality_score = (resolution_score * 0.5 + blur_score * 0.5)
    
    # Generate recommendations
    recommendations = []
    if not resolution_ok:
        recommendations.append(f"Image is too small ({width}x{height}). Minimum recommended: 200x200 pixels.")
    if is_blurry:
        recommendations.append("Image appears blurry. Consider uploading a higher quality version.")
    if quality_score < 0.7:
        recommendations.append("Consider using AI logo generation or uploading a better quality image.")
    
    if not recommendations:
        recommendations.append("Logo quality is good!")
    
    return {
        "quality_score": round(quality_score, 2),
        "resolution": {
            "width": width,
            "height": height,
            "meets_minimum": resolution_ok
        },
        "is_blurry": is_blurry,
        "format": format_type,
        "needs_enhancement": quality_score < 0.7,
        "recommendations": recommendations
    }


def check_resolution(image: Image.Image, min_size: int = 200) -> bool:
    """
    Check if image meets minimum resolution requirements.
    
    Args:
        image: PIL Image object
        min_size: Minimum dimension required (default 200px)
        
    Returns:
        True if resolution is acceptable
    """
    width, height = image.size
    return width >= min_size and height >= min_size


def calculate_resolution_score(width: int, height: int) -> float:
    """
    Calculate a resolution score based on image dimensions.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        Score from 0.0 to 1.0
    """
    min_dim = min(width, height)
    
    if min_dim >= 400:
        return 1.0
    elif min_dim >= 200:
        return 0.8
    elif min_dim >= 100:
        return 0.5
    elif min_dim >= 50:
        return 0.3
    else:
        return 0.1


def check_blur(image: Image.Image) -> tuple:
    """
    Detect if an image is blurry using Laplacian variance.
    
    The Laplacian operator highlights regions of rapid intensity change,
    so a blurry image will have low variance in the Laplacian.
    
    Args:
        image: PIL Image object
        
    Returns:
        Tuple of (is_blurry: bool, variance: float)
    """
    # Convert to grayscale
    gray = image.convert('L')
    
    # Convert to numpy array
    gray_array = np.array(gray, dtype=np.float64)
    
    # Calculate Laplacian (approximation using convolution)
    # Laplacian kernel: [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
    laplacian = np.zeros_like(gray_array)
    
    # Apply Laplacian filter manually (avoiding cv2 dependency)
    for i in range(1, gray_array.shape[0] - 1):
        for j in range(1, gray_array.shape[1] - 1):
            laplacian[i, j] = (
                gray_array[i-1, j] + gray_array[i+1, j] +
                gray_array[i, j-1] + gray_array[i, j+1] -
                4 * gray_array[i, j]
            )
    
    # Calculate variance
    variance = laplacian.var()
    
    # Threshold for blur detection (empirically determined)
    # Lower variance = more blur
    BLUR_THRESHOLD = 100
    is_blurry = variance < BLUR_THRESHOLD
    
    return (is_blurry, variance)


def calculate_blur_score(variance: float) -> float:
    """
    Convert blur variance to a quality score.
    
    Args:
        variance: Laplacian variance value
        
    Returns:
        Score from 0.0 to 1.0 (higher = sharper)
    """
    # Map variance to score
    # Very blurry: variance < 50 → score < 0.3
    # Blurry: variance 50-100 → score 0.3-0.6
    # Sharp: variance 100-500 → score 0.6-0.9
    # Very sharp: variance > 500 → score 0.9-1.0
    
    if variance >= 500:
        return 1.0
    elif variance >= 100:
        return 0.6 + (variance - 100) / 400 * 0.4
    elif variance >= 50:
        return 0.3 + (variance - 50) / 50 * 0.3
    else:
        return variance / 50 * 0.3
