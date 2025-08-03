from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://webuser:webpassword@localhost/webaudit_db")

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    overall_score = Column(Integer)
    
    # Individual scores
    speed_score = Column(Integer)
    seo_score = Column(Integer) 
    security_score = Column(Integer)
    mobile_score = Column(Integer)
    
    # Detailed data (JSON format)
    speed_data = Column(JSON)
    seo_data = Column(JSON)
    security_data = Column(JSON)
    mobile_data = Column(JSON)
    
    # Screenshots (base64)
    desktop_screenshot = Column(Text, nullable=True)
    mobile_screenshot = Column(Text, nullable=True)
    
    # Metadata
    analysis_duration = Column(Float)  # How long analysis took
    user_ip = Column(String)  # For rate limiting
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Performance metrics
    load_time = Column(Float)
    page_size = Column(Integer)  # in bytes
    requests_count = Column(Integer)

class RateLimitLog(Base):
    __tablename__ = "rate_limit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True)
    request_count = Column(Integer, default=1)
    window_start = Column(DateTime, default=datetime.utcnow)
    last_request = Column(DateTime, default=datetime.utcnow)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Database utilities
class DatabaseManager:
    @staticmethod
    def save_analysis(db, url: str, results: dict, user_ip: str, duration: float):
        """Save analysis results to database"""
        analysis = AnalysisResult(
            url=url,
            overall_score=results["overall_score"],
            speed_score=results["speed"]["score"],
            seo_score=results["seo"]["score"],
            security_score=results["security"]["score"],
            mobile_score=results["mobile"]["score"],
            speed_data=results["speed"],
            seo_data=results["seo"],
            security_data=results["security"],
            mobile_data=results["mobile"],
            desktop_screenshot=results.get("screenshots", {}).get("desktop"),
            mobile_screenshot=results.get("screenshots", {}).get("mobile"),
            analysis_duration=duration,
            user_ip=user_ip,
            load_time=results["speed"].get("load_time", 0),
            page_size=results["speed"].get("page_size", 0),
            requests_count=results["speed"].get("requests_count", 0)
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    
    @staticmethod
    def get_cached_analysis(db, url: str, cache_hours: int = 1):
        """Get cached analysis if recent enough"""
        cutoff_time = datetime.utcnow() - timedelta(hours=cache_hours)
        
        return db.query(AnalysisResult).filter(
            AnalysisResult.url == url,
            AnalysisResult.created_at > cutoff_time
        ).first()
    
    @staticmethod
    def get_recent_analyses(db, limit: int = 10):
        """Get recent analyses for homepage showcase"""
        return db.query(AnalysisResult).order_by(
            AnalysisResult.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def check_rate_limit(db, ip_address: str, max_per_hour: int = 10):
        """Simple rate limiting check"""
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        recent_count = db.query(AnalysisResult).filter(
            AnalysisResult.user_ip == ip_address,
            AnalysisResult.created_at > hour_ago
        ).count()
        
        return recent_count < max_per_hour