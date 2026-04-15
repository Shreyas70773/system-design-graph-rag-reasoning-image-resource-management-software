"""
Brand Consistency Validator Module
Validates generated content against brand guidelines.
"""
from typing import Dict, Any, List, Optional

from app.scraping.color_extractor import compare_colors, hex_to_rgb


async def calculate_brand_score(
    brand_context: Dict[str, Any],
    image_url: Optional[str],
    colors_extracted: List[str]
) -> float:
    """
    Calculate how well generated content matches brand guidelines.
    
    Factors:
    - Color consistency with brand palette
    - (Future: Style consistency, typography, etc.)
    
    Args:
        brand_context: Brand data from Neo4j
        image_url: URL of generated image
        colors_extracted: Colors extracted from generated image
        
    Returns:
        Score from 0.0 to 1.0
    """
    if not colors_extracted:
        return 0.5  # Neutral score if we can't analyze
    
    brand_colors = brand_context.get('colors', [])
    if not brand_colors:
        return 0.7  # Decent score if brand has no defined colors
    
    # Calculate color consistency
    color_score = calculate_color_consistency(
        [c.get('hex', '') for c in brand_colors if c.get('hex')],
        colors_extracted
    )
    
    # For now, color is the main factor
    # Future: Add more validation factors
    brand_score = color_score
    
    return round(brand_score, 2)


def calculate_color_consistency(
    brand_colors: List[str],
    generated_colors: List[str]
) -> float:
    """
    Calculate how well generated colors match brand palette.
    
    Uses color similarity comparison to find matches.
    
    Args:
        brand_colors: List of brand hex colors
        generated_colors: List of hex colors from generated image
        
    Returns:
        Consistency score from 0.0 to 1.0
    """
    if not brand_colors or not generated_colors:
        return 0.5
    
    total_similarity = 0
    comparisons = 0
    
    # Check how many generated colors are close to brand colors
    for gen_color in generated_colors[:5]:  # Top 5 generated colors
        best_match = 0
        for brand_color in brand_colors:
            similarity = compare_colors(gen_color, brand_color)
            if similarity > best_match:
                best_match = similarity
        
        total_similarity += best_match
        comparisons += 1
    
    if comparisons == 0:
        return 0.5
    
    # Average similarity
    avg_similarity = total_similarity / comparisons
    
    # Boost score if at least one color is a strong match (>0.8)
    has_strong_match = any(
        compare_colors(gen, brand) > 0.8
        for gen in generated_colors[:3]
        for brand in brand_colors
    )
    
    if has_strong_match:
        avg_similarity = min(1.0, avg_similarity + 0.15)
    
    return avg_similarity


def validate_color_palette(
    brand_colors: List[str],
    generated_colors: List[str],
    threshold: float = 0.6
) -> Dict[str, Any]:
    """
    Detailed validation of generated colors against brand palette.
    
    Args:
        brand_colors: List of brand hex colors
        generated_colors: List of hex colors from generated image
        threshold: Minimum similarity to consider a match
        
    Returns:
        Dict with matches, mismatches, and recommendations
    """
    matches = []
    mismatches = []
    
    for gen_color in generated_colors:
        best_match = None
        best_similarity = 0
        
        for brand_color in brand_colors:
            similarity = compare_colors(gen_color, brand_color)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = brand_color
        
        if best_similarity >= threshold:
            matches.append({
                "generated": gen_color,
                "brand_match": best_match,
                "similarity": best_similarity
            })
        else:
            mismatches.append({
                "generated": gen_color,
                "closest_brand": best_match,
                "similarity": best_similarity
            })
    
    # Generate recommendations
    recommendations = []
    if len(mismatches) > len(matches):
        recommendations.append("Consider regenerating with stronger brand color emphasis")
    if not matches:
        recommendations.append("Generated image doesn't contain brand colors")
    
    return {
        "matches": matches,
        "mismatches": mismatches,
        "match_percentage": len(matches) / len(generated_colors) * 100 if generated_colors else 0,
        "recommendations": recommendations
    }
