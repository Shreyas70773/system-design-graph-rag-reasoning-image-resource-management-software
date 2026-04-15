"""
Text Overlay Compositing Module
Places generated text on top of images with proper styling.
"""
import io
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Dict, Any, Optional, Tuple, List
import textwrap
import os


# Available fonts for selection (web-safe fonts with fallbacks)
AVAILABLE_FONTS = {
    "montserrat": {
        "name": "Montserrat",
        "description": "Modern, clean sans-serif",
        "style": "modern",
        "file": "Montserrat-Bold.ttf"
    },
    "playfair": {
        "name": "Playfair Display",
        "description": "Elegant serif for luxury brands",
        "style": "elegant",
        "file": "PlayfairDisplay-Bold.ttf"
    },
    "roboto": {
        "name": "Roboto",
        "description": "Versatile, professional sans-serif",
        "style": "professional",
        "file": "Roboto-Bold.ttf"
    },
    "poppins": {
        "name": "Poppins",
        "description": "Friendly, geometric sans-serif",
        "style": "friendly",
        "file": "Poppins-Bold.ttf"
    },
    "oswald": {
        "name": "Oswald",
        "description": "Bold, impactful condensed",
        "style": "bold",
        "file": "Oswald-Bold.ttf"
    },
    "lora": {
        "name": "Lora",
        "description": "Balanced serif for readability",
        "style": "classic",
        "file": "Lora-Bold.ttf"
    },
    "raleway": {
        "name": "Raleway",
        "description": "Sleek, minimalist sans-serif",
        "style": "minimalist",
        "file": "Raleway-Bold.ttf"
    },
    "bebas": {
        "name": "Bebas Neue",
        "description": "All-caps display font",
        "style": "display",
        "file": "BebasNeue-Regular.ttf"
    }
}

# Text placement options
TEXT_LAYOUTS = {
    "top_centered": {
        "headline_position": "top_center",
        "body_position": "below_headline",
        "padding_top": 0.08,
        "padding_sides": 0.1
    },
    "bottom_centered": {
        "headline_position": "bottom_center",
        "body_position": "above_headline", 
        "padding_bottom": 0.08,
        "padding_sides": 0.1
    },
    "center_overlay": {
        "headline_position": "center",
        "body_position": "below_headline",
        "padding_sides": 0.1
    },
    "bottom_left": {
        "headline_position": "bottom_left",
        "body_position": "below_headline",
        "padding_bottom": 0.1,
        "padding_left": 0.08
    }
}


def get_available_fonts() -> List[Dict[str, str]]:
    """Return list of available fonts for frontend selection"""
    return [
        {"id": key, **value}
        for key, value in AVAILABLE_FONTS.items()
    ]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_contrasting_color(bg_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Calculate contrasting text color (black or white)"""
    # Calculate luminance
    luminance = (0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]) / 255
    return (255, 255, 255) if luminance < 0.5 else (0, 0, 0)


def get_dominant_color_region(image: Image.Image, region: str = "center") -> Tuple[int, int, int]:
    """Get dominant color from a specific region of the image"""
    width, height = image.size
    
    if region == "top":
        box = (0, 0, width, height // 3)
    elif region == "bottom":
        box = (0, 2 * height // 3, width, height)
    elif region == "center":
        margin_x = width // 4
        margin_y = height // 4
        box = (margin_x, margin_y, width - margin_x, height - margin_y)
    else:
        box = (0, 0, width, height)
    
    region_image = image.crop(box).resize((50, 50))
    colors = region_image.getcolors(2500)
    if colors:
        most_common = max(colors, key=lambda x: x[0])[1]
        if len(most_common) == 4:  # RGBA
            return most_common[:3]
        return most_common
    return (128, 128, 128)


def load_font(font_id: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font by ID, with fallback to default"""
    # Try to load from local fonts directory
    fonts_dir = os.path.join(os.path.dirname(__file__), "..", "fonts")
    
    if font_id in AVAILABLE_FONTS:
        font_file = AVAILABLE_FONTS[font_id]["file"]
        font_path = os.path.join(fonts_dir, font_file)
        
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                pass
    
    # Try common system font locations
    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
    ]
    
    for font_path in system_fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
    
    # Ultimate fallback - default PIL font (will be small)
    return ImageFont.load_default()


def add_text_shadow(
    draw: ImageDraw.ImageDraw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 128),
    offset: int = 3
) -> None:
    """Add shadow effect to text"""
    x, y = position
    # Draw shadow
    draw.text((x + offset, y + offset), text, font=font, fill=shadow_color)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def create_gradient_overlay(
    size: Tuple[int, int],
    direction: str = "bottom",
    color: Tuple[int, int, int] = (0, 0, 0),
    opacity_start: int = 0,
    opacity_end: int = 180
) -> Image.Image:
    """Create a gradient overlay for better text readability"""
    width, height = size
    overlay = Image.new('RGBA', size, (0, 0, 0, 0))
    
    for y in range(height):
        if direction == "bottom":
            # Gradient from top (transparent) to bottom (opaque)
            progress = y / height
        elif direction == "top":
            # Gradient from bottom (transparent) to top (opaque)
            progress = 1 - (y / height)
        else:
            progress = 0.5
        
        opacity = int(opacity_start + (opacity_end - opacity_start) * progress)
        
        for x in range(width):
            overlay.putpixel((x, y), (*color, opacity))
    
    return overlay


def composite_text_on_image(
    image_bytes: bytes,
    headline: Optional[str],
    body_copy: Optional[str],
    brand_context: Dict[str, Any],
    layout: str = "bottom_centered"
) -> bytes:
    """
    Composite text overlay on the generated image.
    
    Args:
        image_bytes: The base image bytes
        headline: Headline text to overlay
        body_copy: Body copy text to overlay
        brand_context: Brand data including font preferences and colors
        layout: Text placement layout
        
    Returns:
        Composited image bytes
    """
    # Open the image
    image = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
    width, height = image.size
    
    # Get brand preferences
    font_id = brand_context.get('font_id', 'montserrat')
    brand_colors = brand_context.get('colors', [])
    
    # Determine text color based on layout position
    if layout in ["bottom_centered", "bottom_left"]:
        region = "bottom"
    elif layout == "top_centered":
        region = "top"
    else:
        region = "center"
    
    # Get background color in text region
    bg_color = get_dominant_color_region(image, region)
    
    # Use primary brand color for text if available and contrasts well
    if brand_colors:
        primary_hex = brand_colors[0].get('hex', '#FFFFFF')
        primary_rgb = hex_to_rgb(primary_hex)
        # Check if brand color contrasts with background
        bg_luminance = (0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]) / 255
        primary_luminance = (0.299 * primary_rgb[0] + 0.587 * primary_rgb[1] + 0.114 * primary_rgb[2]) / 255
        
        # If good contrast, use brand color; otherwise use contrasting black/white
        if abs(bg_luminance - primary_luminance) > 0.4:
            text_color = primary_rgb
        else:
            text_color = get_contrasting_color(bg_color)
    else:
        text_color = get_contrasting_color(bg_color)
    
    # Create overlay layer for text
    text_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    
    # Calculate dimensions
    padding_sides = int(width * 0.08)
    padding_vertical = int(height * 0.06)
    max_text_width = width - (padding_sides * 2)
    
    # Load fonts
    headline_font_size = int(height * 0.08)  # 8% of image height
    body_font_size = int(height * 0.04)  # 4% of image height
    
    headline_font = load_font(font_id, headline_font_size)
    body_font = load_font(font_id, body_font_size)
    
    # Add gradient overlay for readability
    if layout in ["bottom_centered", "bottom_left"]:
        gradient = create_gradient_overlay((width, height // 2), "bottom", (0, 0, 0), 0, 160)
        gradient_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        gradient_layer.paste(gradient, (0, height // 2))
        image = Image.alpha_composite(image, gradient_layer)
    elif layout == "top_centered":
        gradient = create_gradient_overlay((width, height // 2), "top", (0, 0, 0), 0, 160)
        gradient_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        gradient_layer.paste(gradient, (0, 0))
        image = Image.alpha_composite(image, gradient_layer)
    
    # Recalculate draw on text layer
    draw = ImageDraw.Draw(text_layer)
    
    # Calculate text positions based on layout
    if layout == "bottom_centered":
        current_y = height - padding_vertical
        
        # Draw body copy first (at bottom)
        if body_copy:
            body_lines = wrap_text(body_copy, body_font, max_text_width, draw)
            body_lines.reverse()  # Start from bottom
            for line in body_lines:
                bbox = draw.textbbox((0, 0), line, font=body_font)
                line_height = bbox[3] - bbox[1]
                line_width = bbox[2] - bbox[0]
                x = (width - line_width) // 2
                current_y -= line_height + 5
                
                # Add shadow
                add_text_shadow(draw, (x, current_y), line, body_font)
                draw.text((x, current_y), line, font=body_font, fill=(*text_color, 255))
            
            current_y -= int(height * 0.03)  # Gap between body and headline
        
        # Draw headline above body
        if headline:
            headline_lines = wrap_text(headline.upper(), headline_font, max_text_width, draw)
            headline_lines.reverse()
            for line in headline_lines:
                bbox = draw.textbbox((0, 0), line, font=headline_font)
                line_height = bbox[3] - bbox[1]
                line_width = bbox[2] - bbox[0]
                x = (width - line_width) // 2
                current_y -= line_height + 8
                
                add_text_shadow(draw, (x, current_y), line, headline_font, offset=4)
                draw.text((x, current_y), line, font=headline_font, fill=(*text_color, 255))
    
    elif layout == "top_centered":
        current_y = padding_vertical
        
        # Draw headline first (at top)
        if headline:
            headline_lines = wrap_text(headline.upper(), headline_font, max_text_width, draw)
            for line in headline_lines:
                bbox = draw.textbbox((0, 0), line, font=headline_font)
                line_height = bbox[3] - bbox[1]
                line_width = bbox[2] - bbox[0]
                x = (width - line_width) // 2
                
                add_text_shadow(draw, (x, current_y), line, headline_font, offset=4)
                draw.text((x, current_y), line, font=headline_font, fill=(*text_color, 255))
                current_y += line_height + 8
            
            current_y += int(height * 0.02)
        
        # Draw body below headline
        if body_copy:
            body_lines = wrap_text(body_copy, body_font, max_text_width, draw)
            for line in body_lines:
                bbox = draw.textbbox((0, 0), line, font=body_font)
                line_height = bbox[3] - bbox[1]
                line_width = bbox[2] - bbox[0]
                x = (width - line_width) // 2
                
                add_text_shadow(draw, (x, current_y), line, body_font)
                draw.text((x, current_y), line, font=body_font, fill=(*text_color, 255))
                current_y += line_height + 5
    
    elif layout == "center_overlay":
        # Calculate total text height
        total_height = 0
        headline_lines = []
        body_lines = []
        
        if headline:
            headline_lines = wrap_text(headline.upper(), headline_font, max_text_width, draw)
            for line in headline_lines:
                bbox = draw.textbbox((0, 0), line, font=headline_font)
                total_height += bbox[3] - bbox[1] + 8
        
        if body_copy:
            total_height += int(height * 0.03)  # Gap
            body_lines = wrap_text(body_copy, body_font, max_text_width, draw)
            for line in body_lines:
                bbox = draw.textbbox((0, 0), line, font=body_font)
                total_height += bbox[3] - bbox[1] + 5
        
        current_y = (height - total_height) // 2
        
        # Draw headline
        for line in headline_lines:
            bbox = draw.textbbox((0, 0), line, font=headline_font)
            line_height = bbox[3] - bbox[1]
            line_width = bbox[2] - bbox[0]
            x = (width - line_width) // 2
            
            add_text_shadow(draw, (x, current_y), line, headline_font, offset=4)
            draw.text((x, current_y), line, font=headline_font, fill=(*text_color, 255))
            current_y += line_height + 8
        
        if headline_lines and body_lines:
            current_y += int(height * 0.02)
        
        # Draw body
        for line in body_lines:
            bbox = draw.textbbox((0, 0), line, font=body_font)
            line_height = bbox[3] - bbox[1]
            line_width = bbox[2] - bbox[0]
            x = (width - line_width) // 2
            
            add_text_shadow(draw, (x, current_y), line, body_font)
            draw.text((x, current_y), line, font=body_font, fill=(*text_color, 255))
            current_y += line_height + 5
    
    elif layout == "bottom_left":
        current_y = height - padding_vertical
        padding_left = int(width * 0.08)
        
        if body_copy:
            body_lines = wrap_text(body_copy, body_font, max_text_width * 0.7, draw)
            body_lines.reverse()
            for line in body_lines:
                bbox = draw.textbbox((0, 0), line, font=body_font)
                line_height = bbox[3] - bbox[1]
                current_y -= line_height + 5
                
                add_text_shadow(draw, (padding_left, current_y), line, body_font)
                draw.text((padding_left, current_y), line, font=body_font, fill=(*text_color, 255))
            
            current_y -= int(height * 0.02)
        
        if headline:
            headline_lines = wrap_text(headline.upper(), headline_font, max_text_width * 0.8, draw)
            headline_lines.reverse()
            for line in headline_lines:
                bbox = draw.textbbox((0, 0), line, font=headline_font)
                line_height = bbox[3] - bbox[1]
                current_y -= line_height + 8
                
                add_text_shadow(draw, (padding_left, current_y), line, headline_font, offset=4)
                draw.text((padding_left, current_y), line, font=headline_font, fill=(*text_color, 255))
    
    # Composite text layer onto image
    result = Image.alpha_composite(image, text_layer)
    
    # Convert to RGB for output
    result = result.convert('RGB')
    
    # Save to bytes
    output = io.BytesIO()
    result.save(output, format='PNG', quality=95)
    output.seek(0)
    
    return output.getvalue()


def add_logo_to_image(
    image_bytes: bytes,
    logo_bytes: bytes,
    position: str = "bottom_right",
    scale: float = 0.12,
    padding: float = 0.03,
    opacity: float = 0.9
) -> bytes:
    """
    Add a logo watermark to an image.
    
    Args:
        image_bytes: The base image bytes
        logo_bytes: The logo image bytes
        position: Where to place the logo (top_left, top_right, bottom_left, bottom_right, center)
        scale: Logo size as fraction of image width (default 12%)
        padding: Padding from edge as fraction of image size (default 3%)
        opacity: Logo opacity (0-1, default 0.9)
        
    Returns:
        Image bytes with logo composited
    """
    # Open images
    image = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
    logo = Image.open(io.BytesIO(logo_bytes)).convert('RGBA')
    
    img_width, img_height = image.size
    
    # Calculate logo size (scaled to image width)
    target_width = int(img_width * scale)
    aspect = logo.width / logo.height
    target_height = int(target_width / aspect)
    
    # Resize logo
    logo = logo.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Apply opacity
    if opacity < 1.0:
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        logo.putalpha(alpha)
    
    # Calculate position
    pad_x = int(img_width * padding)
    pad_y = int(img_height * padding)
    
    if position == "top_left":
        pos = (pad_x, pad_y)
    elif position == "top_right":
        pos = (img_width - target_width - pad_x, pad_y)
    elif position == "bottom_left":
        pos = (pad_x, img_height - target_height - pad_y)
    elif position == "bottom_right":
        pos = (img_width - target_width - pad_x, img_height - target_height - pad_y)
    elif position == "center":
        pos = ((img_width - target_width) // 2, (img_height - target_height) // 2)
    else:
        pos = (img_width - target_width - pad_x, img_height - target_height - pad_y)  # Default: bottom_right
    
    # Create transparent layer and paste logo
    logo_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    logo_layer.paste(logo, pos, logo)
    
    # Composite
    result = Image.alpha_composite(image, logo_layer)
    result = result.convert('RGB')
    
    # Save to bytes
    output = io.BytesIO()
    result.save(output, format='PNG', quality=95)
    output.seek(0)
    
    return output.getvalue()


def get_text_layouts() -> List[Dict[str, str]]:
    """Return available text layout options"""
    return [
        {"id": "bottom_centered", "name": "Bottom Centered", "description": "Text centered at bottom with gradient"},
        {"id": "top_centered", "name": "Top Centered", "description": "Text centered at top with gradient"},
        {"id": "center_overlay", "name": "Center Overlay", "description": "Text centered in middle of image"},
        {"id": "bottom_left", "name": "Bottom Left", "description": "Text aligned left at bottom"}
    ]
