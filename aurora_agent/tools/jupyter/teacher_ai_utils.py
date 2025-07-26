# File: session-bubble/aurora_agent/tools/jupyter/teacher_ai_utils.py

# High-level functions for common pedagogical scenarios in Jupyter notebooks

import logging
import asyncio
from typing import List, Dict, Optional
from .annotation_tool import (
    annotate_and_click_cell_n,
    clear_all_annotations,
    get_cell_at_viewport_position,
    edit_cell_with_scaffolding,
    highlight_cell_for_doubt_resolution
)
from .reader_tool import read_code_of_cell_n, read_output_of_cell_n

logger = logging.getLogger(__name__)

class TeacherAI:
    """High-level Teacher AI interface for Jupyter notebook interactions."""
    
    @staticmethod
    async def model_concept(cell_number: int, concept_name: str, explanation: str = None) -> str:
        """
        MODELLING: Demonstrate a concept by highlighting and explaining a cell.
        Used when teacher wants to show "how to do something".
        """
        annotation_text = f"📚 Modelling: {concept_name}"
        if explanation:
            annotation_text += f" - {explanation}"
            
        result = await annotate_and_click_cell_n(cell_number, "blue", annotation_text)
        logger.info(f"Modelling concept '{concept_name}' in cell {cell_number}")
        return result
    
    @staticmethod
    async def provide_scaffolding(target_cell: int, support_content: str, guidance_message: str) -> str:
        """
        SCAFFOLDING: Provide structured support by editing a cell with guidance.
        Used when student needs help but should still do some work themselves.
        """
        scaffold_message = f"🏗️ Scaffolding: {guidance_message}"
        result = await edit_cell_with_scaffolding(target_cell, support_content, scaffold_message)
        logger.info(f"Providing scaffolding for cell {target_cell}: {guidance_message}")
        return result
    
    @staticmethod
    async def coach_problem_solving(cell_number: int, hint: str, problem_context: str = None) -> str:
        """
        COACHING: Guide student through problem-solving by highlighting and providing hints.
        Used when student is working through a problem and needs guidance.
        """
        context = f" - {problem_context}" if problem_context else ""
        annotation_text = f"🎯 Coaching: {hint}{context}"
        
        result = await annotate_and_click_cell_n(cell_number, "green", annotation_text)
        logger.info(f"Coaching problem-solving in cell {cell_number}: {hint}")
        return result
    
    @staticmethod
    async def handle_student_doubt(cell_number: int, doubt_description: str) -> Dict[str, str]:
        """
        Handle when a student expresses doubt about a specific cell.
        Returns both the cell content and highlighting result for context.
        """
        # Highlight the cell for doubt resolution
        highlight_result = await highlight_cell_for_doubt_resolution(cell_number, doubt_description)
        
        # Get the cell content for context
        cell_content = await read_code_of_cell_n(cell_number)
        cell_output = await read_output_of_cell_n(cell_number)
        
        logger.info(f"Handling student doubt about cell {cell_number}: {doubt_description}")
        
        return {
            "highlight_result": highlight_result,
            "cell_content": cell_content,
            "cell_output": cell_output,
            "doubt_description": doubt_description
        }
    
    @staticmethod
    async def identify_cell_from_student_reference(reference_description: str, search_area: str = "center") -> Optional[int]:
        """
        Try to identify which cell a student is referring to based on their description.
        
        Args:
            reference_description: Student's description like "this cell", "the one above", etc.
            search_area: "center", "top", "bottom" - where to look in viewport
        """
        position_map = {
            "center": (50, 50),
            "top": (50, 25),
            "bottom": (50, 75),
            "current": (50, 50)  # Default to center
        }
        
        x, y = position_map.get(search_area, (50, 50))
        
        # Try to detect cell at the specified position
        detection_result = await get_cell_at_viewport_position(x, y)
        
        if "Success" in detection_result and "Cell" in detection_result:
            # Extract cell number from result
            import re
            match = re.search(r'Cell (\d+)', detection_result)
            if match:
                cell_number = int(match.group(1))
                logger.info(f"Identified cell {cell_number} from student reference: {reference_description}")
                return cell_number
        
        logger.warning(f"Could not identify cell from reference: {reference_description}")
        return None
    
    @staticmethod
    async def create_learning_sequence(cells_and_concepts: List[Dict[str, any]]) -> str:
        """
        Create a sequence of annotations for a learning progression.
        
        Args:
            cells_and_concepts: List of dicts with keys: 'cell', 'type', 'message', 'color'
        """
        results = []
        
        for i, item in enumerate(cells_and_concepts):
            cell_num = item['cell']
            pedagogy_type = item.get('type', 'modelling')
            message = item['message']
            color = item.get('color', 'blue')
            
            # Add pedagogical prefix based on type
            prefixes = {
                'modelling': '📚',
                'scaffolding': '🏗️',
                'coaching': '🎯'
            }
            
            prefix = prefixes.get(pedagogy_type, '📚')
            annotation_text = f"{prefix} {pedagogy_type.title()}: {message}"
            
            result = await annotate_and_click_cell_n(cell_num, color, annotation_text)
            results.append(f"Step {i+1}: {result}")
            
            # Brief pause between annotations for visual effect
            if i < len(cells_and_concepts) - 1:
                await asyncio.sleep(1)
        
        logger.info(f"Created learning sequence with {len(cells_and_concepts)} steps")
        return "\n".join(results)
    
    @staticmethod
    async def demonstrate_error_correction(error_cell: int, corrected_code: str, explanation: str) -> str:
        """
        Demonstrate how to fix an error by scaffolding the correction.
        Perfect for teaching debugging and error handling.
        """
        # First highlight the error
        await highlight_cell_for_doubt_resolution(error_cell, "Error detected - let's fix this!")
        await asyncio.sleep(2)
        
        # Then provide scaffolding with the correction
        scaffold_message = f"🔧 Error Correction: {explanation}"
        result = await edit_cell_with_scaffolding(error_cell, corrected_code, scaffold_message)
        
        logger.info(f"Demonstrated error correction for cell {error_cell}: {explanation}")
        return result
    
    @staticmethod
    async def reset_teaching_session() -> str:
        """Clear all annotations to start fresh."""
        result = await clear_all_annotations()
        logger.info("Teaching session reset - all annotations cleared")
        return result

# Convenience functions for quick access
async def model(cell: int, concept: str, explanation: str = None) -> str:
    """Quick modelling function."""
    return await TeacherAI.model_concept(cell, concept, explanation)

async def scaffold(cell: int, content: str, guidance: str) -> str:
    """Quick scaffolding function."""
    return await TeacherAI.provide_scaffolding(cell, content, guidance)

async def coach(cell: int, hint: str, context: str = None) -> str:
    """Quick coaching function."""
    return await TeacherAI.coach_problem_solving(cell, hint, context)

async def handle_doubt(cell: int, doubt: str) -> Dict[str, str]:
    """Quick doubt handling function."""
    return await TeacherAI.handle_student_doubt(cell, doubt)