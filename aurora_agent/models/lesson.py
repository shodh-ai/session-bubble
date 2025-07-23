"""Database models for lesson plan persistence."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Lesson(Base):
    """Main lesson plan table."""
    __tablename__ = "lessons"
    
    lesson_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    creator_id = Column(String(100), nullable=False)  # User ID who created the lesson
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to lesson steps
    steps = relationship("LessonStep", back_populates="lesson", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert lesson to dictionary for API responses."""
        return {
            "lesson_id": self.lesson_id,
            "title": self.title,
            "creator_id": self.creator_id,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "steps": [step.to_dict() for step in self.steps] if self.steps else []
        }

class LessonStep(Base):
    """Individual steps within a lesson plan."""
    __tablename__ = "lesson_steps"
    
    step_id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.lesson_id"), nullable=False)
    step_number = Column(Integer, nullable=False)  # Order of the step in the lesson
    narration = Column(Text, nullable=False)  # Teacher's narration for this step
    action_data = Column(JSON, nullable=False)  # Complete action data from verification system
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to parent lesson
    lesson = relationship("Lesson", back_populates="steps")
    
    def to_dict(self):
        """Convert lesson step to dictionary for API responses."""
        return {
            "step_id": self.step_id,
            "lesson_id": self.lesson_id,
            "step_number": self.step_number,
            "narration": self.narration,
            "action_data": self.action_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
