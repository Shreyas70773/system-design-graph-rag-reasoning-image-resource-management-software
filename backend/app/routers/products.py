"""
Product management endpoints
- Parse products from text
- Scrape products from URL
- Smart scrape single product with AI extraction
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

router = APIRouter()


# === Request/Response Models ===

class ParseTextRequest(BaseModel):
    """Request to parse products from text"""
    text: str


class ScrapeProductsRequest(BaseModel):
    """Request to scrape products from URL"""
    url: HttpUrl


class SmartScrapeRequest(BaseModel):
    """Request to smart scrape a single product page"""
    url: HttpUrl


class ProductInfo(BaseModel):
    """Product information"""
    name: str
    price: Optional[str] = None
    price_range: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


class SmartProductInfo(BaseModel):
    """Detailed product info from smart scrape"""
    name: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    price_range: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None
    key_features: Optional[List[str]] = None


class ProductsResponse(BaseModel):
    """Response containing parsed products"""
    products: List[ProductInfo]
    source: str  # "text_parsing" or "url_scraping"


# === Endpoints ===

@router.post("/{brand_id}/products/parse-text", response_model=ProductsResponse)
async def parse_products_from_text(brand_id: str, request: ParseTextRequest):
    """
    Parse products from a text description using Groq LLM.
    
    Example input: "We sell coffee ($15), cold brew ($5), and pastries ($3-8)"
    
    Returns structured product data extracted by AI.
    """
    from app.products.text_parser import parse_products_with_llm
    from app.database.neo4j_client import neo4j_client
    
    # Verify brand exists
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    try:
        products = await parse_products_with_llm(request.text)
        
        # Save products to Neo4j
        neo4j_client.add_products_to_brand(brand_id, products)
        
        return ProductsResponse(products=products, source="text_parsing")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{brand_id}/products/scrape-url", response_model=ProductsResponse)
async def scrape_products_from_url(brand_id: str, request: ScrapeProductsRequest):
    """
    Scrape products from a product page URL.
    
    Attempts to extract product cards/items from the page.
    """
    from app.products.url_scraper import scrape_product_page
    from app.database.neo4j_client import neo4j_client
    
    # Verify brand exists
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    try:
        products = await scrape_product_page(str(request.url))
        
        # Save products to Neo4j
        neo4j_client.add_products_to_brand(brand_id, products)
        
        return ProductsResponse(products=products, source="url_scraping")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{brand_id}/products")
async def get_brand_products(brand_id: str):
    """Get all products for a brand"""
    from app.database.neo4j_client import neo4j_client
    
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    products = neo4j_client.get_brand_products(brand_id)
    return {"brand_id": brand_id, "products": products}


@router.post("/{brand_id}/products")
async def add_products(brand_id: str, products: List[ProductInfo]):
    """Manually add products to a brand"""
    from app.database.neo4j_client import neo4j_client
    
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    neo4j_client.add_products_to_brand(brand_id, [p.dict() for p in products])
    return {"message": f"Added {len(products)} products to brand", "brand_id": brand_id}


@router.post("/{brand_id}/products/smart-scrape", response_model=SmartProductInfo)
async def smart_scrape_product(brand_id: str, request: SmartScrapeRequest):
    """
    Smart scrape a single product page using AI to extract detailed info.
    
    Scrapes the page, extracts images and text, then uses OpenAI/Groq to
    intelligently extract product name, summary, description, price, etc.
    """
    from app.products.smart_scraper import scrape_product_url
    from app.database.neo4j_client import neo4j_client
    
    # Verify brand exists
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    try:
        product_data = await scrape_product_url(str(request.url))
        
        # Save to Neo4j if we got a name
        if product_data.get('name'):
            product_for_db = {
                'name': product_data['name'],
                'price': product_data.get('price'),
                'description': product_data.get('description') or product_data.get('summary'),
                'category': product_data.get('category'),
                'image_url': product_data.get('image_url')
            }
            neo4j_client.add_products_to_brand(brand_id, [product_for_db])
        
        return SmartProductInfo(**product_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape product: {str(e)}")
