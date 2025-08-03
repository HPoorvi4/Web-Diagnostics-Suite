from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Request Models
class AnalysisRequest(BaseModel):
    url: HttpUrl = Field(..., description="Website URL to analyze")
    include_screenshots: bool = Field(default=True, description="Include mobile/desktop screenshots")
    
class HistoryRequest(BaseModel):
    limit: int = Field(default=10, le=50, description="Number of recent analyses to return")

# Response Models
class SpeedAnalysisResult(BaseModel):
    load_time: float = Field(..., description="Page load time in seconds")
    first_contentful_paint: float = Field(..., description="FCP in milliseconds")
    largest_contentful_paint: float = Field(..., description="LCP in milliseconds")
    page_size: int = Field(..., description="Total page size in bytes")
    requests_count: int = Field(..., description="Total number of HTTP requests")
    score: int = Field(..., ge=0, le=100, description="Speed score 0-100")
    grade: str = Field(..., description="Letter grade A-F")
    recommendations: List[str] = Field(default=[], description="Speed improvement suggestions")

class SEOAnalysisResult(BaseModel):
    title: Dict[str, Any] = Field(..., description="Title tag analysis")
    meta_description: Dict[str, Any] = Field(..., description="Meta description analysis")
    headings: Dict[str, Any] = Field(..., description="Heading structure analysis")
    images: Dict[str, Any] = Field(..., description="Image optimization analysis")
    score: int = Field(..., ge=0, le=100, description="SEO score 0-100")
    grade: str = Field(..., description="Letter grade A-F")
    issues: List[str] = Field(default=[], description="SEO issues found")
    recommendations: List[str] = Field(default=[], description="SEO improvement suggestions")

class SecurityAnalysisResult(BaseModel):
    ssl_status: Dict[str, Any] = Field(..., description="SSL certificate status")
    https_redirect: bool = Field(..., description="HTTP to HTTPS redirect enabled")
    security_headers: Dict[str, Any] = Field(..., description="Security headers analysis")
    score: int = Field(..., ge=0, le=100, description="Security score 0-100")
    grade: str = Field(..., description="Letter grade A-F")
    vulnerabilities: List[str] = Field(default=[], description="Security issues found")
    recommendations: List[str] = Field(default=[], description="Security improvement suggestions")

class MobileAnalysisResult(BaseModel):
    viewport_meta: bool = Field(..., description="Has proper viewport meta tag")
    responsive_design: Dict[str, Any] = Field(..., description="Responsive design analysis")
    touch_friendly: Dict[str, Any] = Field(..., description="Touch-friendly elements analysis")
    mobile_performance: Dict[str, Any] = Field(..., description="Mobile-specific performance")
    score: int = Field(..., ge=0, le=100, description="Mobile score 0-100")
    grade: str = Field(..., description="Letter grade A-F")
    issues: List[str] = Field(default=[], description="Mobile usability issues")
    recommendations: List[str] = Field(default=[], description="Mobile improvement suggestions")

class ScreenshotData(BaseModel):
    desktop: Optional[str] = Field(None, description="Desktop screenshot (base64)")
    mobile: Optional[str] = Field(None, description="Mobile screenshot (base64)")

class AnalysisResponse(BaseModel):
    id: int = Field(..., description="Analysis ID")
    url: str = Field(..., description="Analyzed URL")
    overall_score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    overall_grade: str = Field(..., description="Overall letter grade A-F")
    
    # Analysis results
    speed: SpeedAnalysisResult
    seo: SEOAnalysisResult
    security: SecurityAnalysisResult
    mobile: MobileAnalysisResult
    
    # Screenshots
    screenshots: Optional[ScreenshotData] = None
    
    # Metadata
    analysis_duration: float = Field(..., description="Time taken for analysis in seconds")
    analyzed_at: datetime = Field(..., description="When analysis was performed")
    cached: bool = Field(default=False, description="Whether result was cached")
    
    # Summary
    top_recommendations: List[str] = Field(..., description="Top 3 improvement recommendations")
    critical_issues: List[str] = Field(default=[], description="Critical issues requiring immediate attention")

class AnalysisProgress(BaseModel):
    session_id: str = Field(..., description="WebSocket session ID")
    stage: str = Field(..., description="Current analysis stage")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    message: str = Field(..., description="Progress message")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated seconds remaining")

class RecentAnalysis(BaseModel):
    id: int
    url: str
    overall_score: int
    overall_grade: str
    analyzed_at: datetime
    
class AnalysisHistory(BaseModel):
    total_count: int = Field(..., description="Total number of analyses")
    recent_analyses: List[RecentAnalysis] = Field(..., description="Recent analysis results")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    database_connected: bool = Field(..., description="Database connection status")
    browser_ready: bool = Field(..., description="Browser automation ready status")
    version: str = Field(default="1.0.0", description="API version")

# Utility Models
class GradeCalculator:
    @staticmethod
    def get_grade(score: int) -> str:
        """Convert numerical score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    @staticmethod
    def get_grade_color(grade: str) -> str:
        """Get color for grade display"""
        colors = {
            "A": "#10b981",  # Green
            "B": "#3b82f6",  # Blue  
            "C": "#f59e0b",  # Yellow
            "D": "#f97316",  # Orange
            "F": "#ef4444"   # Red
        }
        return colors.get(grade, "#6b7280")