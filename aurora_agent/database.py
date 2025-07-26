# File: session-bubble/aurora_agent/database.py

"""
Database models and setup for Aurora Agent OAuth token storage.
"""
import os
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime

Base = declarative_base()

class UserToken(Base):
    """Store OAuth tokens for users."""
    __tablename__ = "user_tokens"
    
    user_id = Column(String, primary_key=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=True)
    scopes = Column(Text, nullable=True)  # JSON string of scopes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database setup
DATABASE_PATH = os.getenv("DATABASE_PATH", "/tmp/aurora_agent.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

# Async engine for FastAPI
async_engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def create_tables():
    """Create database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
