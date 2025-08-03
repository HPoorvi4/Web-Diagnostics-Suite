from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import asyncio
import uuid
from datetime import datetime, timedelta
import logging
from typing import Dict

# Import our modules
from database import get_db, create_tables, DatabaseManager
from models import (
    AnalysisRequest, AnalysisResponse, AnalysisHistory, 
    HealthResponse, ErrorResponse, AnalysisProgress
)
from services.analysis_service import AnalysisService
from utils.rate_limiter import RateLimiter
from utils.validators import URLValidator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_progress(self, session_id: str, progress_data: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(progress_data)
            except Exception as e:
                logger.error(f"Error sending progress to {session_id}: {e}")
                self.disconnect(session_id)

# Initialize connection manager
manager = ConnectionManager()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting WebAudit Pro API...")
    create_tables()
    
    # Initialize browser pool for analysis service
    analysis_service = AnalysisService()
    await analysis_service.initialize()
    
    # Store in app state
    app.state.analysis_service = analysis_service
    app.state.rate_limiter = RateLimiter()
    
    logger.info("API startup complete!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down WebAudit Pro API...")
    await app.state.analysis_service.cleanup()

# Create FastAPI app
app = FastAPI(
    title="WebAudit Pro API",
    description="Professional web diagnostics and analysis suite",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility function to get client IP
def get_client_ip(request):
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

# Routes

@app.get("/", response_model=dict)
async def root():
    """API root endpoint"""
    return {
        "service": "WebAudit Pro API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_connected = True
    except Exception:
        db_connected = False
    
    # Check if analysis service is ready
    browser_ready = hasattr(app.state, 'analysis_service') and app.state.analysis_service.is_ready()
    
    return HealthResponse(
        status="healthy" if db_connected and browser_ready else "degraded",
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        browser_ready=browser_ready
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_website(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    client_ip: str = Depends(get_client_ip)
):
    """Analyze a website - main endpoint"""
    try:
        # Validate URL
        if not URLValidator.is_valid_url(str(request.url)):
            raise HTTPException(
                status_code=400,
                detail="Invalid URL format"
            )
        
        # Check rate limiting
        if not app.state.rate_limiter.check_rate_limit(db, client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Check cache first
        cached_result = DatabaseManager.get_cached_analysis(db, str(request.url))
        if cached_result:
            logger.info(f"Returning cached result for {request.url}")
            return AnalysisResponse(
                id=cached_result.id,
                url=cached_result.url,
                overall_score=cached_result.overall_score,
                overall_grade=GradeCalculator.get_grade(cached_result.overall_score),
                speed=cached_result.speed_data,
                seo=cached_result.seo_data,
                security=cached_result.security_data,
                mobile=cached_result.mobile_data,
                screenshots={
                    "desktop": cached_result.desktop_screenshot,
                    "mobile": cached_result.mobile_screenshot
                } if request.include_screenshots else None,
                analysis_duration=cached_result.analysis_duration,
                analyzed_at=cached_result.created_at,
                cached=True,
                top_recommendations=[], # We'll populate this from the data
                critical_issues=[]
            )
        
        # Perform new analysis
        start_time = datetime.utcnow()
        session_id = str(uuid.uuid4())
        
        # Send analysis to background task
        background_tasks.add_task(
            perform_background_analysis,
            str(request.url),
            session_id,
            request.include_screenshots,
            client_ip,
            db
        )
        
        # Return session for real-time updates
        return JSONResponse(
            status_code=202,
            content={
                "message": "Analysis started",
                "session_id": session_id,
                "websocket_url": f"/ws/{session_id}",
                "estimated_duration": "30-60 seconds"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing {request.url}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during analysis"
        )

async def perform_background_analysis(
    url: str, 
    session_id: str, 
    include_screenshots: bool,
    client_ip: str,
    db: Session
):
    """Perform analysis in background with progress updates"""
    try:
        # Initialize analysis service
        analysis_service = app.state.analysis_service
        
        # Send initial progress
        await manager.send_progress(session_id, {
            "stage": "Starting analysis...",
            "progress": 0,
            "message": "Initializing browser and validators"
        })
        
        # Perform analysis with progress updates
        results = await analysis_service.analyze_website(
            url=url,
            include_screenshots=include_screenshots,
            progress_callback=lambda stage, progress, message: asyncio.create_task(
                manager.send_progress(session_id, {
                    "stage": stage,
                    "progress": progress,
                    "message": message
                })
            )
        )
        
        # Save to database
        analysis_duration = (datetime.utcnow() - datetime.utcnow()).total_seconds()
        saved_analysis = DatabaseManager.save_analysis(
            db, url, results, client_ip, analysis_duration
        )
        
        # Send completion
        await manager.send_progress(session_id, {
            "stage": "Complete!",
            "progress": 100,
            "message": "Analysis finished successfully",
            "analysis_id": saved_analysis.id,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Background analysis failed for {url}: {e}")
        await manager.send_progress(session_id, {
            "stage": "Error",
            "progress": 0,
            "message": f"Analysis failed: {str(e)}",
            "error": True
        })

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)

@app.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Get specific analysis by ID"""
    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return AnalysisResponse(
        id=analysis.id,
        url=analysis.url,
        overall_score=analysis.overall_score,
        overall_grade=GradeCalculator.get_grade(analysis.overall_score),
        speed=analysis.speed_data,
        seo=analysis.seo_data,
        security=analysis.security_data,
        mobile=analysis.mobile_data,
        screenshots={
            "desktop": analysis.desktop_screenshot,
            "mobile": analysis.mobile_screenshot
        },
        analysis_duration=analysis.analysis_duration,
        analyzed_at=analysis.created_at,
        cached=False,
        top_recommendations=extract_top_recommendations(analysis),
        critical_issues=extract_critical_issues(analysis)
    )

@app.get("/history", response_model=AnalysisHistory)
async def get_analysis_history(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get recent analysis history"""
    try:
        recent_analyses = DatabaseManager.get_recent_analyses(db, limit)
        
        return AnalysisHistory(
            total_count=len(recent_analyses),
            recent_analyses=[
                {
                    "id": analysis.id,
                    "url": analysis.url,
                    "overall_score": analysis.overall_score,
                    "overall_grade": GradeCalculator.get_grade(analysis.overall_score),
                    "analyzed_at": analysis.created_at
                }
                for analysis in recent_analyses
            ]
        )
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching analysis history")

@app.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Delete specific analysis"""
    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
    
    return {"message": "Analysis deleted successfully"}

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get basic statistics"""
    try:
        total_analyses = db.query(AnalysisResult).count()
        today_analyses = db.query(AnalysisResult).filter(
            AnalysisResult.created_at >= datetime.utcnow().date()
        ).count()
        
        # Average scores
        avg_speed = db.query(func.avg(AnalysisResult.speed_score)).scalar() or 0
        avg_seo = db.query(func.avg(AnalysisResult.seo_score)).scalar() or 0
        avg_security = db.query(func.avg(AnalysisResult.security_score)).scalar() or 0
        avg_mobile = db.query(func.avg(AnalysisResult.mobile_score)).scalar() or 0
        
        return {
            "total_analyses": total_analyses,
            "today_analyses": today_analyses,
            "average_scores": {
                "speed": round(avg_speed, 1),
                "seo": round(avg_seo, 1),
                "security": round(avg_security, 1),
                "mobile": round(avg_mobile, 1)
            }
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {
            "total_analyses": 0,
            "today_analyses": 0,
            "average_scores": {"speed": 0, "seo": 0, "security": 0, "mobile": 0}
        }

# Helper functions
def extract_top_recommendations(analysis) -> List[str]:
    """Extract top 3 recommendations from analysis data"""
    recommendations = []
    
    # Add recommendations from each category
    if analysis.speed_data and "recommendations" in analysis.speed_data:
        recommendations.extend(analysis.speed_data["recommendations"][:2])
    
    if analysis.seo_data and "recommendations" in analysis.seo_data:
        recommendations.extend(analysis.seo_data["recommendations"][:2])
    
    if analysis.security_data and "recommendations" in analysis.security_data:
        recommendations.extend(analysis.security_data["recommendations"][:1])
    
    return recommendations[:3]  # Top 3 only

def extract_critical_issues(analysis) -> List[str]:
    """Extract critical issues requiring immediate attention"""
    critical_issues = []
    
    # Check for critical security issues
    if analysis.security_score < 60:
        critical_issues.append("Critical security vulnerabilities detected")
    
    # Check for critical speed issues  
    if analysis.speed_score < 50:
        critical_issues.append("Very slow page load times affecting user experience")
    
    # Check for critical SEO issues
    if analysis.seo_score < 40:
        critical_issues.append("Major SEO issues preventing search visibility")
    
    return critical_issues

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={"message": str(exc)}
        ).dict()
    )

# Rate limiting exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 429:
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error="Rate limit exceeded",
                error_code="RATE_LIMIT_EXCEEDED",
                details={"message": "Too many requests. Please try again later."}
            ).dict()
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code="HTTP_ERROR"
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )