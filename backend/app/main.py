import sys
import asyncio
import os

# CRITICAL: Windows Playwright fix - must be at the very top
if sys.platform == "win32":
    # Install nest_asyncio to allow nested event loops
    try:
        import nest_asyncio
        nest_asyncio.apply()
        print("Applied nest_asyncio for Windows compatibility")
    except ImportError:
        print("WARNING: nest_asyncio not found. Install with: pip install nest-asyncio")
        print("Attempting to use ProactorEventLoop...")
        try:
            # Use ProactorEventLoop for better Windows subprocess support
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except:
            # Fallback to default
            pass

import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from database import AnalysisResult  
from sqlalchemy import func 
import uuid
from datetime import datetime, timedelta
from typing import Dict
import traceback
from sqlalchemy import text

# Import our modules
from database import get_db, create_tables, DatabaseManager
from models import (
    AnalysisRequest, AnalysisResponse, AnalysisHistory, 
    HealthResponse, ErrorResponse, AnalysisProgress,
    SpeedAnalysisResult, SEOAnalysisResult, SecurityAnalysisResult, MobileAnalysisResult
)
from services.analysis_service import AnalysisService
from utils.rate_limiter import RateLimiter
from utils.validators import URLValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
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

# Grade calculator utility
class GradeCalculator:
    @staticmethod
    def get_grade(score: int) -> str:
        """Convert numeric score to letter grade"""
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

# Lifespan context manager with better Windows error handling
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting WebAudit Pro API...")
    
    try:
        # Test database connection first
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful!")
        
        # Create tables
        create_tables()
        logger.info("Database tables created/verified!")
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Please ensure PostgreSQL is running and credentials are correct")
        logger.error("Current DATABASE_URL expects: postgresql://webuser:webpassword@localhost:5432/webaudit_db")
        raise
    
    try:
        # Initialize analysis service with Windows-specific handling
        logger.info("Initializing analysis service...")
        analysis_service = AnalysisService()
        
        # Special Windows initialization with timeout
        if sys.platform == "win32":
            logger.info("Detected Windows - applying special Playwright initialization...")
            try:
                # Try initialization with timeout
                await asyncio.wait_for(analysis_service.initialize(), timeout=30.0)
                logger.info("Windows Playwright initialization successful!")
            except asyncio.TimeoutError:
                logger.error("Playwright initialization timed out (30s)")
                raise Exception("Playwright initialization timed out - check your Windows setup")
            except Exception as e:
                if "NotImplementedError" in str(e) or "subprocess" in str(e):
                    logger.error("=" * 60)
                    logger.error("WINDOWS PLAYWRIGHT SETUP ISSUE")
                    logger.error("=" * 60)
                    logger.error("Your Windows system needs additional setup for Playwright:")
                    logger.error("")
                    logger.error("SOLUTION 1: Install nest-asyncio")
                    logger.error("  pip install nest-asyncio")
                    logger.error("")
                    logger.error("SOLUTION 2: Complete Playwright Windows setup")
                    logger.error("  1. pip uninstall playwright")
                    logger.error("  2. pip install playwright")
                    logger.error("  3. playwright install")
                    logger.error("  4. playwright install-deps")
                    logger.error("")
                    logger.error("SOLUTION 3: Run in Windows Subsystem for Linux (WSL)")
                    logger.error("  1. Install WSL2")
                    logger.error("  2. Install Ubuntu from Microsoft Store")
                    logger.error("  3. Run your project in WSL environment")
                    logger.error("")
                    logger.error("SOLUTION 4: Use Docker")
                    logger.error("  docker run -p 8000:8000 your-app")
                    logger.error("=" * 60)
                raise e
        else:
            # Non-Windows initialization
            await analysis_service.initialize()
        
        # Store in app state
        app.state.analysis_service = analysis_service
        app.state.rate_limiter = RateLimiter()
        
        logger.info("API startup complete!")
        
    except Exception as e:
        logger.error(f"Failed to initialize analysis service: {e}")
        logger.error(f"Error details: {traceback.format_exc()}")
        
        # Create a dummy service for basic functionality
        app.state.analysis_service = None
        app.state.rate_limiter = RateLimiter()
        logger.warning("Running in LIMITED MODE - analysis features disabled")
        logger.warning("The API will work for basic endpoints but website analysis will not function")
    
    yield
    
    # Shutdown
    logger.info("Shutting down WebAudit Pro API...")
    if hasattr(app.state, 'analysis_service') and app.state.analysis_service:
        try:
            await app.state.analysis_service.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

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
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility function to get client IP
def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# Routes

@app.get("/", response_model=dict)
async def root():
    """API root endpoint"""
    analysis_available = (hasattr(app.state, 'analysis_service') and 
                         app.state.analysis_service is not None)
    
    return {
        "service": "WebAudit Pro API",
        "version": "1.0.0",
        "status": "running",
        "analysis_available": analysis_available,
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze" if analysis_available else "/analyze (disabled)",
            "history": "/history",
            "stats": "/stats"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_connected = False
    
    # Check if analysis service is ready
    browser_ready = (hasattr(app.state, 'analysis_service') and 
                    app.state.analysis_service and 
                    app.state.analysis_service.is_ready())
    
    status = "healthy"
    if not db_connected:
        status = "unhealthy"
    elif not browser_ready:
        status = "degraded"
    
    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        browser_ready=browser_ready
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_website(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    client_request: Request,
    db: Session = Depends(get_db)
):
    """Analyze a website - main endpoint"""
    try:
        client_ip = get_client_ip(client_request)
        
        # Check if analysis service is available
        if not app.state.analysis_service:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Analysis service is currently unavailable",
                    "reason": "Playwright initialization failed",
                    "solutions": [
                        "Install nest-asyncio: pip install nest-asyncio",
                        "Reinstall Playwright: pip install --force-reinstall playwright",
                        "Use Windows Subsystem for Linux (WSL)",
                        "Use Docker container"
                    ]
                }
            )
        
        # Validate URL
        validator = URLValidator()
        is_valid, error_message = validator.is_valid_url(str(request.url))
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL: {error_message}"
            )
        
        # Check rate limiting (optional - uncomment if needed)
        # if not app.state.rate_limiter.check_rate_limit(db, client_ip):
        #     raise HTTPException(
        #         status_code=429,
        #         detail="Rate limit exceeded. Please try again later."
        #     )
        
        # Check cache first
        cached_result = DatabaseManager.get_cached_analysis(db, str(request.url))
        if cached_result:
            logger.info(f"Returning cached result for {request.url}")
            return build_analysis_response(cached_result, True)
        
        # Perform new analysis
        session_id = str(uuid.uuid4())
        
        # Send analysis to background task
        background_tasks.add_task(
            perform_background_analysis,
            str(request.url),
            session_id,
            request.include_screenshots,
            client_ip
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
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Internal server error during analysis"
        )

def build_analysis_response(analysis: AnalysisResult, cached: bool = False) -> AnalysisResponse:
    """Build AnalysisResponse from database result"""
    try:
        # Create proper nested response objects
        speed = SpeedAnalysisResult(
            load_time=analysis.load_time or 0.0,
            first_contentful_paint=analysis.speed_data.get('first_contentful_paint', 0.0) if analysis.speed_data else 0.0,
            largest_contentful_paint=analysis.speed_data.get('largest_contentful_paint', 0.0) if analysis.speed_data else 0.0,
            page_size=analysis.page_size or 0,
            requests_count=analysis.requests_count or 0,
            score=analysis.speed_score,
            grade=GradeCalculator.get_grade(analysis.speed_score),
            recommendations=analysis.speed_data.get('recommendations', []) if analysis.speed_data else []
        )
        
        seo = SEOAnalysisResult(
            title=analysis.seo_data.get('title', {}) if analysis.seo_data else {},
            meta_description=analysis.seo_data.get('meta_description', {}) if analysis.seo_data else {},
            headings=analysis.seo_data.get('headings', {}) if analysis.seo_data else {},
            images=analysis.seo_data.get('images', {}) if analysis.seo_data else {},
            score=analysis.seo_score,
            grade=GradeCalculator.get_grade(analysis.seo_score),
            issues=analysis.seo_data.get('issues', []) if analysis.seo_data else [],
            recommendations=analysis.seo_data.get('recommendations', []) if analysis.seo_data else []
        )
        
        security = SecurityAnalysisResult(
            ssl_status=analysis.security_data.get('ssl_status', {}) if analysis.security_data else {},
            https_redirect=analysis.security_data.get('https_redirect', False) if analysis.security_data else False,
            security_headers=analysis.security_data.get('security_headers', {}) if analysis.security_data else {},
            score=analysis.security_score,
            grade=GradeCalculator.get_grade(analysis.security_score),
            vulnerabilities=analysis.security_data.get('vulnerabilities', []) if analysis.security_data else [],
            recommendations=analysis.security_data.get('recommendations', []) if analysis.security_data else []
        )
        
        mobile = MobileAnalysisResult(
            viewport_meta=analysis.mobile_data.get('viewport_meta', False) if analysis.mobile_data else False,
            responsive_design=analysis.mobile_data.get('responsive_design', {}) if analysis.mobile_data else {},
            touch_friendly=analysis.mobile_data.get('touch_friendly', {}) if analysis.mobile_data else {},
            mobile_performance=analysis.mobile_data.get('mobile_performance', {}) if analysis.mobile_data else {},
            score=analysis.mobile_score,
            grade=GradeCalculator.get_grade(analysis.mobile_score),
            issues=analysis.mobile_data.get('issues', []) if analysis.mobile_data else [],
            recommendations=analysis.mobile_data.get('recommendations', []) if analysis.mobile_data else []
        )
        
        return AnalysisResponse(
            id=analysis.id,
            url=analysis.url,
            overall_score=analysis.overall_score,
            overall_grade=GradeCalculator.get_grade(analysis.overall_score),
            speed=speed,
            seo=seo,
            security=security,
            mobile=mobile,
            screenshots={
                "desktop": analysis.desktop_screenshot,
                "mobile": analysis.mobile_screenshot
            } if analysis.desktop_screenshot or analysis.mobile_screenshot else None,
            analysis_duration=analysis.analysis_duration,
            analyzed_at=analysis.created_at,
            cached=cached,
            top_recommendations=extract_top_recommendations(analysis),
            critical_issues=extract_critical_issues(analysis)
        )
    except Exception as e:
        logger.error(f"Error building analysis response: {e}")
        raise

async def perform_background_analysis(
    url: str, 
    session_id: str, 
    include_screenshots: bool,
    client_ip: str
):
    """Perform analysis in background with progress updates"""
    db = None
    analysis_id = None
    
    try:
        logger.info(f"Starting analysis #{session_id[:8]} for URL: {url}")
        
        # Get database session
        db = next(get_db())
        
        # Initialize analysis service
        analysis_service = app.state.analysis_service
        
        # Define progress callback
        async def send_progress_update(stage, progress, message, error=False):
            """Send progress update via WebSocket"""
            try:
                await manager.send_progress(session_id, {
                    "stage": stage,
                    "progress": progress,
                    "message": message,
                    "error": error
                })
            except Exception as e:
                logger.error(f"Error sending progress update: {e}")
        
        # Send initial progress
        await send_progress_update("Starting analysis...", 0, "Initializing browser and validators")
        
        start_time = datetime.utcnow()
        
        # Perform analysis with progress updates
        results = await analysis_service.analyze_website(
            url=url,
            include_screenshots=include_screenshots,
            progress_callback=send_progress_update
        )
        
        # Calculate duration
        analysis_duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Analysis #{session_id[:8]} completed successfully in {analysis_duration:.1f}s. Score: {results.get('overall_score', 0)}/100")
        
        # Save to database
        saved_analysis = DatabaseManager.save_analysis(
            db=db,
            url=url,
            results=results,
            user_ip=client_ip,
            duration=analysis_duration
        )
        analysis_id = saved_analysis.id
        
        await send_progress_update("Complete!", 100, "Analysis finished successfully")
        
        # Build and send final results
        response = build_analysis_response(saved_analysis, False)
        
        # Send final results
        await manager.send_progress(session_id, {
            "stage": "Complete!",
            "progress": 100,
            "message": "Analysis finished successfully",
            "analysis_id": analysis_id,
            "results": response.dict()
        })
        
    except Exception as e:
        logger.error(f"Background analysis failed for {url}: {e}")
        logger.error(traceback.format_exc())
        await manager.send_progress(session_id, {
            "stage": "Error",
            "progress": 0,
            "message": f"Analysis failed: {str(e)}",
            "error": True
        })
    finally:
        if db:
            db.close()

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
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        manager.disconnect(session_id)

@app.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Get specific analysis by ID"""
    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return build_analysis_response(analysis, False)

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
            },
            "analysis_available": app.state.analysis_service is not None
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {
            "total_analyses": 0,
            "today_analyses": 0,
            "average_scores": {"speed": 0, "seo": 0, "security": 0, "mobile": 0},
            "analysis_available": False
        }

# Helper functions
def extract_top_recommendations(analysis) -> list[str]:
    """Extract top 3 recommendations from analysis data"""
    recommendations = []
    
    # Add recommendations from each category
    if analysis.speed_data and isinstance(analysis.speed_data, dict) and "recommendations" in analysis.speed_data:
        recommendations.extend(analysis.speed_data["recommendations"][:2])
    
    if analysis.seo_data and isinstance(analysis.seo_data, dict) and "recommendations" in analysis.seo_data:
        recommendations.extend(analysis.seo_data["recommendations"][:2])
    
    if analysis.security_data and isinstance(analysis.security_data, dict) and "recommendations" in analysis.security_data:
        recommendations.extend(analysis.security_data["recommendations"][:1])
    
    return recommendations[:3]  # Top 3 only

def extract_critical_issues(analysis) -> list[str]:
    """Extract critical issues requiring immediate attention"""
    critical_issues = []
    
    # Check for critical security issues
    if analysis.security_score and analysis.security_score < 60:
        critical_issues.append("Critical security vulnerabilities detected")
    
    # Check for critical speed issues  
    if analysis.speed_score and analysis.speed_score < 50:
        critical_issues.append("Very slow page load times affecting user experience")
    
    # Check for critical SEO issues
    if analysis.seo_score and analysis.seo_score < 40:
        critical_issues.append("Major SEO issues preventing search visibility")
    
    return critical_issues

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    logger.error(traceback.format_exc())
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

def main():
    """Main function with Windows compatibility"""
    import uvicorn
    
    # Get URL from command line args
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if url:
        os.environ["TARGET_URL"] = url
    
    # Windows-specific message
    if sys.platform == "win32":
        print("=" * 60)
        print("STARTING WEBAUDIT PRO ON WINDOWS")
        print("=" * 60)
        print("If you encounter Playwright issues, try:")
        print("1. pip install nest-asyncio")
        print("2. playwright install")
        print("3. Use WSL2 for better compatibility")
        print("=" * 60)
    
    # Run with the correct module path
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload on Windows to prevent event loop issues
        log_level="info"
    )

if __name__ == "__main__":
    main()