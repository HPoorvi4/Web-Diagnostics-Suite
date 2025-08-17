from datetime import datetime, timedelta
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, JSON,
    func, and_, text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
import base64
import json
from dotenv import load_dotenv


# Setup logging
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# Load environment variables
load_dotenv()

# Database configuration with detailed logging
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL not found in environment variables!")
    DATABASE_URL = "postgresql://webuser:webpassword@localhost:5433/webaudit_db"
    logger.info(f"Using default DATABASE_URL: {DATABASE_URL}")
else:
    # Log the DATABASE_URL (but hide password for security)
    safe_url = DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('://')[1], "***:***")
    logger.info(f"Loaded DATABASE_URL from .env: {safe_url}")

print(f"DEBUG: Current working directory: {os.getcwd()}")
print(f"DEBUG: .env file exists: {os.path.exists('.env')}")
print(f"DEBUG: DATABASE_URL from env: {DATABASE_URL}")

# Create engine with better error handling
try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,    # Refresh connections every 5 minutes
        connect_args={
            "connect_timeout": 10,
            "application_name": "WebAudit_Pro"
        }
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Utility function to handle JSON serialization of bytes objects
def serialize_analysis_data(data):
    """Convert bytes objects to base64 strings for JSON serialization"""
    if isinstance(data, dict):
        return {k: serialize_analysis_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_analysis_data(item) for item in data]
    elif isinstance(data, bytes):
        # Convert bytes to base64 string
        return {
            "_type": "base64",
            "data": base64.b64encode(data).decode('utf-8')
        }
    else:
        return data

def deserialize_analysis_data(data):
    """Convert base64 strings back to bytes objects when reading from database"""
    if isinstance(data, dict):
        if data.get("_type") == "base64":
            return base64.b64decode(data["data"])
        else:
            return {k: deserialize_analysis_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [deserialize_analysis_data(item) for item in data]
    else:
        return data

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

# Create tables with better error handling
def create_tables():
    """Create database tables with better error handling"""
    try:
        logger.info("Creating database tables...")
        
        # Test connection first
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version}")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        logger.error("Please check:")
        logger.error("1. PostgreSQL server is running")
        logger.error("2. Database 'webaudit_db' exists")
        logger.error("3. User 'webuser' exists and has correct password")
        logger.error("4. User 'webuser' has permissions on the database")
        raise

# Database utilities
class DatabaseManager:
    @staticmethod
    def save_analysis(db, url: str, results: dict, user_ip: str, duration: float):
        """Save analysis results to database with proper JSON serialization"""
        try:
            # Serialize all JSON data to handle bytes objects
            speed_data = serialize_analysis_data(results.get("speed", {}))
            seo_data = serialize_analysis_data(results.get("seo", {}))
            security_data = serialize_analysis_data(results.get("security", {}))
            mobile_data = serialize_analysis_data(results.get("mobile", {}))
            
            # Handle screenshots separately - they should be base64 strings or None
            screenshots = results.get("screenshots", {})
            desktop_screenshot = screenshots.get("desktop")
            mobile_screenshot = screenshots.get("mobile")
            
            # Convert screenshot bytes to base64 if they're bytes objects
            if isinstance(desktop_screenshot, bytes):
                desktop_screenshot = base64.b64encode(desktop_screenshot).decode('utf-8')
            
            if isinstance(mobile_screenshot, bytes):
                mobile_screenshot = base64.b64encode(mobile_screenshot).decode('utf-8')
            
            analysis = AnalysisResult(
                url=url,
                overall_score=results.get("overall_score", 0),
                speed_score=results.get("speed", {}).get("score", 0),
                seo_score=results.get("seo", {}).get("score", 0),
                security_score=results.get("security", {}).get("score", 0),
                mobile_score=results.get("mobile", {}).get("score", 0),
                speed_data=speed_data,
                seo_data=seo_data,
                security_data=security_data,
                mobile_data=mobile_data,
                desktop_screenshot=desktop_screenshot,
                mobile_screenshot=mobile_screenshot,
                analysis_duration=duration,
                user_ip=user_ip,
                load_time=results.get("speed", {}).get("load_time", 0),
                page_size=results.get("speed", {}).get("page_size", 0),
                requests_count=results.get("speed", {}).get("requests_count", 0)
            )
            
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            logger.info(f"Analysis saved with ID: {analysis.id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def save_analysis_new_format(analysis_data: dict):
        """Alternative save method for new format (if called from main.py)"""
        with SessionLocal() as db:
            try:
                # Serialize JSON data to handle bytes objects
                serialized_data = {
                    'url': analysis_data['url'],
                    'overall_score': analysis_data['overall_score'],
                    'speed_score': analysis_data['speed_score'],
                    'seo_score': analysis_data['seo_score'],
                    'security_score': analysis_data['security_score'],
                    'mobile_score': analysis_data['mobile_score'],
                    'speed_data': serialize_analysis_data(analysis_data['speed_data']),
                    'seo_data': serialize_analysis_data(analysis_data['seo_data']),
                    'security_data': serialize_analysis_data(analysis_data['security_data']),
                    'mobile_data': serialize_analysis_data(analysis_data['mobile_data']),
                    'analysis_duration': analysis_data['analysis_duration'],
                    'user_ip': analysis_data['user_ip'],
                    'created_at': analysis_data['created_at'],
                    'load_time': analysis_data.get('load_time'),
                    'page_size': analysis_data.get('page_size'),
                    'requests_count': analysis_data.get('requests_count'),
                }
                
                # Handle screenshots
                desktop_screenshot = analysis_data.get('desktop_screenshot')
                mobile_screenshot = analysis_data.get('mobile_screenshot')
                
                if isinstance(desktop_screenshot, bytes):
                    serialized_data['desktop_screenshot'] = base64.b64encode(desktop_screenshot).decode('utf-8')
                else:
                    serialized_data['desktop_screenshot'] = desktop_screenshot
                
                if isinstance(mobile_screenshot, bytes):
                    serialized_data['mobile_screenshot'] = base64.b64encode(mobile_screenshot).decode('utf-8')
                else:
                    serialized_data['mobile_screenshot'] = mobile_screenshot
                
                analysis_result = AnalysisResult(**serialized_data)
                db.add(analysis_result)
                db.commit()
                db.refresh(analysis_result)
                logger.info(f"Analysis saved with ID: {analysis_result.id}")
                return analysis_result
                
            except Exception as e:
                logger.error(f"Failed to save analysis: {e}")
                logger.error(f"Error details: {type(e).__name__}: {str(e)}")
                db.rollback()
                raise
    
    @staticmethod
    def get_cached_analysis(db, url: str, cache_hours: int = 1):
        """Get cached analysis if recent enough"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=cache_hours)
            
            result = db.query(AnalysisResult).filter(
                AnalysisResult.url == url,
                AnalysisResult.created_at > cutoff_time
            ).first()
            
            if result:
                logger.info(f"Found cached analysis for {url}")
                # Deserialize JSON data when retrieving
                if result.speed_data:
                    result.speed_data = deserialize_analysis_data(result.speed_data)
                if result.seo_data:
                    result.seo_data = deserialize_analysis_data(result.seo_data)
                if result.security_data:
                    result.security_data = deserialize_analysis_data(result.security_data)
                if result.mobile_data:
                    result.mobile_data = deserialize_analysis_data(result.mobile_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get cached analysis: {e}")
            return None
    
    @staticmethod
    def get_recent_analyses(db, limit: int = 10):
        """Get recent analyses for homepage showcase"""
        try:
            results = db.query(AnalysisResult).order_by(
                AnalysisResult.created_at.desc()
            ).limit(limit).all()
            
            # Deserialize JSON data for each result
            for result in results:
                if result.speed_data:
                    result.speed_data = deserialize_analysis_data(result.speed_data)
                if result.seo_data:
                    result.seo_data = deserialize_analysis_data(result.seo_data)
                if result.security_data:
                    result.security_data = deserialize_analysis_data(result.security_data)
                if result.mobile_data:
                    result.mobile_data = deserialize_analysis_data(result.mobile_data)
            
            return results
        except Exception as e:
            logger.error(f"Failed to get recent analyses: {e}")
            return []
    
    @staticmethod
    def check_rate_limit(db, ip_address: str, max_per_hour: int = 10):
        """Simple rate limiting check"""
        try:
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            recent_count = db.query(AnalysisResult).filter(
                AnalysisResult.user_ip == ip_address,
                AnalysisResult.created_at > hour_ago
            ).count()
            
            logger.info(f"Rate limit check for {ip_address}: {recent_count}/{max_per_hour}")
            return recent_count < max_per_hour
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return True  # Allow request if rate limit check fails

# Test database connection function
def test_connection():
    """Test database connection and provide detailed feedback"""
    try:
        logger.info("Testing database connection...")
        
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT current_user, current_database(), version()"))
            user, db_name, version = result.fetchone()
            
            logger.info(f"✅ Connected successfully!")
            logger.info(f"   User: {user}")
            logger.info(f"   Database: {db_name}")
            logger.info(f"   Version: {version}")
            
            # Test if tables exist
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                logger.info(f"   Existing tables: {', '.join(tables)}")
            else:
                logger.info("   No tables found - will be created on startup")
                
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("\n🔧 Troubleshooting steps:")
        logger.error("1. Check if PostgreSQL is running:")
        logger.error("   - Windows: services.msc -> PostgreSQL service")
        logger.error("   - Check if port 5433 is accessible")
        
        logger.error("\n2. Verify database and user exist:")
        logger.error("   Connect to PostgreSQL as admin and run:")
        logger.error("   CREATE DATABASE webaudit_db;")
        logger.error("   CREATE USER webuser WITH PASSWORD 'webpassword';")
        logger.error("   GRANT ALL PRIVILEGES ON DATABASE webaudit_db TO webuser;")
        
        logger.error("\n3. Check your .env file contains:")
        logger.error("   DATABASE_URL=postgresql://webuser:webpassword@localhost:5433/webaudit_db")
        
        return False

if __name__ == "__main__":
    # Run connection test when this file is executed directly
    test_connection()