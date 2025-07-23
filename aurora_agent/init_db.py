"""Initialize database with lesson models."""
from sqlalchemy import create_engine
from database import Base, DATABASE_URL
from models.lesson import Lesson, LessonStep
import logging

logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with all tables."""
    try:
        engine = create_engine(DATABASE_URL, echo=True)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database initialized successfully with lesson tables")
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        print(f"❌ Database initialization failed: {e}")

if __name__ == "__main__":
    init_database()
