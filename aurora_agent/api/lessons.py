"""REST API endpoints for lesson plan management."""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from typing import List, Dict, Any
import logging
from datetime import datetime

from ..models.lesson import Lesson, LessonStep, Base
from ..database import get_db_session

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/lessons", tags=["lessons"])

# Pydantic models for request/response validation
from pydantic import BaseModel

class LessonStepCreate(BaseModel):
    step_number: int
    narration: str
    action_data: Dict[str, Any]

class LessonCreate(BaseModel):
    title: str
    description: str = ""
    creator_id: str = "default_teacher"
    steps: List[LessonStepCreate]

class LessonUpdate(BaseModel):
    title: str = None
    description: str = None
    steps: List[LessonStepCreate] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_lesson(lesson_data: LessonCreate, db: Session = Depends(get_db_session)):
    """Create a new lesson plan with steps."""
    try:
        logger.info(f"Creating new lesson: {lesson_data.title}")
        
        # Create the main lesson record
        new_lesson = Lesson(
            title=lesson_data.title,
            description=lesson_data.description,
            creator_id=lesson_data.creator_id,
            created_at=datetime.utcnow()
        )
        
        db.add(new_lesson)
        db.flush()  # Get the lesson_id without committing
        
        # Create lesson steps
        for step_data in lesson_data.steps:
            lesson_step = LessonStep(
                lesson_id=new_lesson.lesson_id,
                step_number=step_data.step_number,
                narration=step_data.narration,
                action_data=step_data.action_data,
                created_at=datetime.utcnow()
            )
            db.add(lesson_step)
        
        db.commit()
        db.refresh(new_lesson)
        
        logger.info(f"Successfully created lesson with ID: {new_lesson.lesson_id}")
        
        return {
            "lesson_id": new_lesson.lesson_id,
            "title": new_lesson.title,
            "message": "Lesson created successfully",
            "steps_count": len(lesson_data.steps)
        }
        
    except Exception as e:
        logger.error(f"Failed to create lesson: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lesson: {str(e)}"
        )

@router.get("/{lesson_id}")
async def get_lesson(lesson_id: int, db: Session = Depends(get_db_session)):
    """Retrieve a lesson plan by ID."""
    try:
        logger.info(f"Retrieving lesson with ID: {lesson_id}")
        
        lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
        
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
        
        # Convert to dictionary with steps
        lesson_dict = lesson.to_dict()
        
        logger.info(f"Successfully retrieved lesson: {lesson.title}")
        return lesson_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve lesson {lesson_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lesson: {str(e)}"
        )

@router.put("/{lesson_id}")
async def update_lesson(lesson_id: int, lesson_data: LessonUpdate, db: Session = Depends(get_db_session)):
    """Update an existing lesson plan."""
    try:
        logger.info(f"Updating lesson with ID: {lesson_id}")
        
        lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
        
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
        
        # Update lesson fields if provided
        if lesson_data.title is not None:
            lesson.title = lesson_data.title
        if lesson_data.description is not None:
            lesson.description = lesson_data.description
        
        lesson.updated_at = datetime.utcnow()
        
        # Update steps if provided
        if lesson_data.steps is not None:
            # Delete existing steps
            db.query(LessonStep).filter(LessonStep.lesson_id == lesson_id).delete()
            
            # Add new steps
            for step_data in lesson_data.steps:
                lesson_step = LessonStep(
                    lesson_id=lesson_id,
                    step_number=step_data.step_number,
                    narration=step_data.narration,
                    action_data=step_data.action_data,
                    created_at=datetime.utcnow()
                )
                db.add(lesson_step)
        
        db.commit()
        db.refresh(lesson)
        
        logger.info(f"Successfully updated lesson: {lesson.title}")
        
        return {
            "lesson_id": lesson.lesson_id,
            "title": lesson.title,
            "message": "Lesson updated successfully",
            "updated_at": lesson.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update lesson {lesson_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lesson: {str(e)}"
        )

@router.delete("/{lesson_id}")
async def delete_lesson(lesson_id: int, db: Session = Depends(get_db_session)):
    """Delete a lesson plan and all its steps."""
    try:
        logger.info(f"Deleting lesson with ID: {lesson_id}")
        
        lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
        
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
        
        lesson_title = lesson.title
        
        # Delete the lesson (steps will be deleted automatically due to cascade)
        db.delete(lesson)
        db.commit()
        
        logger.info(f"Successfully deleted lesson: {lesson_title}")
        
        return {
            "lesson_id": lesson_id,
            "message": f"Lesson '{lesson_title}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete lesson {lesson_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lesson: {str(e)}"
        )

@router.get("/")
async def list_lessons(creator_id: str = "default_teacher", limit: int = 50, offset: int = 0, db: Session = Depends(get_db_session)):
    """List all lessons for a creator with pagination."""
    try:
        logger.info(f"Listing lessons for creator: {creator_id}")
        
        lessons = db.query(Lesson)\
                   .filter(Lesson.creator_id == creator_id)\
                   .order_by(Lesson.created_at.desc())\
                   .offset(offset)\
                   .limit(limit)\
                   .all()
        
        # Get total count
        total_count = db.query(Lesson).filter(Lesson.creator_id == creator_id).count()
        
        lessons_list = []
        for lesson in lessons:
            lesson_dict = lesson.to_dict()
            # Add step count for summary
            lesson_dict["steps_count"] = len(lesson_dict.get("steps", []))
            lessons_list.append(lesson_dict)
        
        logger.info(f"Retrieved {len(lessons_list)} lessons")
        
        return {
            "lessons": lessons_list,
            "total_count": total_count,
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to list lessons: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list lessons: {str(e)}"
        )

@router.get("/{lesson_id}/steps")
async def get_lesson_steps(lesson_id: int, db: Session = Depends(get_db_session)):
    """Get all steps for a specific lesson."""
    try:
        logger.info(f"Retrieving steps for lesson ID: {lesson_id}")
        
        # Verify lesson exists
        lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with ID {lesson_id} not found"
            )
        
        # Get steps ordered by step number
        steps = db.query(LessonStep)\
                 .filter(LessonStep.lesson_id == lesson_id)\
                 .order_by(LessonStep.step_number)\
                 .all()
        
        steps_list = [step.to_dict() for step in steps]
        
        logger.info(f"Retrieved {len(steps_list)} steps for lesson: {lesson.title}")
        
        return {
            "lesson_id": lesson_id,
            "lesson_title": lesson.title,
            "steps": steps_list,
            "steps_count": len(steps_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve steps for lesson {lesson_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lesson steps: {str(e)}"
        )
