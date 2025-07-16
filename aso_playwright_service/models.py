"""Request/response models for ASO Playwright service."""

from pydantic import BaseModel
from typing import Dict, List, Optional


class KeywordMetrics(BaseModel):
    """Metrics for a keyword from ASO Mobile."""
    difficulty: float
    traffic: float


class AnalyzeKeywordsRequest(BaseModel):
    """Request model for keyword analysis."""
    keywords: List[str]
    correlation_id: Optional[str] = None


class AnalyzeKeywordsResponse(BaseModel):
    """Response model for keyword analysis."""
    metrics: Dict[str, KeywordMetrics]
    status: str
    processing_time: float
    total_keywords: int


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    status: str
    details: str = ""


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    queue_size: int
    service_healthy: bool