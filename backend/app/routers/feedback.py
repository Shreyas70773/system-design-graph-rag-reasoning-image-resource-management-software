"""
Feedback management endpoints
- Submit feedback on generations
- Get feedback statistics
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

router = APIRouter()


# === Request/Response Models ===

class FeedbackRequest(BaseModel):
    """Request to submit feedback"""
    generation_id: str
    rating: Literal["positive", "negative"]
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback submission response"""
    id: str
    generation_id: str
    rating: str
    comment: Optional[str]
    created_at: str


class FeedbackStats(BaseModel):
    """Feedback statistics for a brand"""
    total_feedback: int
    positive_count: int
    negative_count: int
    satisfaction_rate: float


# === Endpoints ===

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback on a generated content piece.
    
    Stores user preference to improve future generations.
    """
    from app.database.neo4j_client import neo4j_client
    
    try:
        feedback_id = neo4j_client.save_feedback(
            generation_id=request.generation_id,
            rating=request.rating,
            comment=request.comment
        )
        
        return FeedbackResponse(
            id=feedback_id,
            generation_id=request.generation_id,
            rating=request.rating,
            comment=request.comment,
            created_at=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{brand_id}/stats", response_model=FeedbackStats)
async def get_feedback_stats(brand_id: str):
    """
    Get feedback statistics for a brand.
    
    Returns counts and satisfaction rate.
    """
    from app.database.neo4j_client import neo4j_client
    
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    try:
        stats = neo4j_client.get_feedback_stats(brand_id)
        return FeedbackStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{brand_id}")
async def get_brand_feedback(brand_id: str, limit: int = 20):
    """Get all feedback for a brand's generations"""
    from app.database.neo4j_client import neo4j_client
    
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    feedback = neo4j_client.get_brand_feedback(brand_id, limit)
    return {"brand_id": brand_id, "feedback": feedback}
