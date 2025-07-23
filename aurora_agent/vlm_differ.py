"""Production VLM differ using Gemini 1.5 Pro for visual analysis."""
import logging
import json
import base64
import re
from typing import Dict, Any, Optional
import google.generativeai as genai
import os
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Configure Gemini API with explicit API key to avoid credential conflicts
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    raise ValueError("GOOGLE_API_KEY is required for VLM analysis")

# Configure with explicit API key only
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# VLM Analysis Prompt with Few-Shot Examples
VLM_ANALYSIS_PROMPT = """
You are an expert visual analyst for Google Sheets interactions. Your task is to analyze two screenshots (before and after) and determine exactly what action the user performed.

You must respond with ONLY a valid JSON object in this exact format:
{
  "tool_name": "action_name",
  "parameters": {
    "cell": "A1",
    "value": "text",
    "range": "A1:B5"
  },
  "description": "Human-readable description",
  "confidence": 0.95,
  "action_category": "cell_edit|formatting|navigation|chart|menu"
}

COMMON ACTIONS TO RECOGNIZE:

1. CELL EDITING:
   - Writing text/numbers in cells
   - Deleting cell content
   - Copy/paste operations

2. FORMATTING:
   - Bold, italic, underline
   - Font size/color changes
   - Cell background colors
   - Borders and alignment

3. NAVIGATION:
   - Cell selection changes
   - Sheet tab switching
   - Scrolling

4. CHARTS:
   - Insert chart dialog
   - Chart type selection
   - Chart customization

5. MENU OPERATIONS:
   - Toolbar button clicks
   - Right-click context menus
   - Insert/delete rows/columns

FEW-SHOT EXAMPLES:

Example 1 - Cell Edit:
If you see text appearing in cell B2 that wasn't there before:
{
  "tool_name": "write_cell",
  "parameters": {
    "cell": "B2",
    "value": "Hello World"
  },
  "description": "User typed 'Hello World' in cell B2",
  "confidence": 0.98,
  "action_category": "cell_edit"
}

Example 2 - Bold Formatting:
If you see a cell's text become bold:
{
  "tool_name": "format_cell",
  "parameters": {
    "cell": "A1",
    "format_type": "bold",
    "value": true
  },
  "description": "User applied bold formatting to cell A1",
  "confidence": 0.92,
  "action_category": "formatting"
}

Example 3 - Chart Creation:
If you see a chart insertion dialog or new chart:
{
  "tool_name": "insert_chart",
  "parameters": {
    "range": "A1:B5",
    "chart_type": "column"
  },
  "description": "User inserted a column chart for range A1:B5",
  "confidence": 0.89,
  "action_category": "chart"
}

ANALYZE THE IMAGES AND RESPOND WITH ONLY THE JSON:
"""

async def analyze_image_diff(before_img: bytes, after_img: bytes) -> Dict[str, Any]:
    """Analyze visual differences using Gemini 1.5 Pro."""
    try:
        logger.info("Starting VLM analysis with Gemini 1.5 Pro")
        
        # Convert bytes to PIL Images
        before_image = Image.open(io.BytesIO(before_img))
        after_image = Image.open(io.BytesIO(after_img))
        
        # Prepare the prompt with images
        prompt_parts = [
            VLM_ANALYSIS_PROMPT,
            "\nBEFORE IMAGE:",
            before_image,
            "\nAFTER IMAGE:",
            after_image,
            "\nAnalyze the differences and respond with JSON only:"
        ]
        
        # Generate response
        response = model.generate_content(prompt_parts)
        raw_response = response.text.strip()
        
        logger.info(f"Raw VLM response: {raw_response[:200]}...")
        
        # Parse and validate JSON response
        parsed_result = _parse_and_validate_response(raw_response)
        
        if parsed_result:
            logger.info(f"Successfully parsed VLM analysis: {parsed_result['tool_name']}")
            return parsed_result
        else:
            # Fallback to mock response if parsing fails
            logger.warning("VLM parsing failed, using fallback response")
            return _get_fallback_response()
            
    except Exception as e:
        logger.error(f"VLM analysis failed: {e}", exc_info=True)
        return _get_fallback_response()

def _parse_and_validate_response(raw_response: str) -> Optional[Dict[str, Any]]:
    """Parse and validate the VLM's JSON response."""
    try:
        # Clean the response - remove markdown formatting, extra text
        cleaned = _clean_json_response(raw_response)
        
        # Parse JSON
        result = json.loads(cleaned)
        
        # Validate required fields
        required_fields = ['tool_name', 'parameters', 'description', 'confidence', 'action_category']
        if not all(field in result for field in required_fields):
            logger.warning(f"Missing required fields in VLM response: {result}")
            return None
            
        # Validate confidence is between 0 and 1
        if not (0 <= result['confidence'] <= 1):
            result['confidence'] = 0.8  # Default confidence
            
        # Validate action_category
        valid_categories = ['cell_edit', 'formatting', 'navigation', 'chart', 'menu']
        if result['action_category'] not in valid_categories:
            result['action_category'] = 'menu'  # Default category
            
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Response validation failed: {e}")
        return None

def _clean_json_response(raw_response: str) -> str:
    """Clean the raw VLM response to extract valid JSON."""
    # Remove markdown code blocks
    cleaned = re.sub(r'```json\s*', '', raw_response)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    
    # Remove any text before the first {
    start_idx = cleaned.find('{')
    if start_idx != -1:
        cleaned = cleaned[start_idx:]
    
    # Remove any text after the last }
    end_idx = cleaned.rfind('}')
    if end_idx != -1:
        cleaned = cleaned[:end_idx + 1]
    
    return cleaned.strip()

def _get_fallback_response() -> Dict[str, Any]:
    """Fallback response when VLM analysis fails."""
    return {
        "tool_name": "unknown_action",
        "parameters": {
            "detected": "visual_change"
        },
        "description": "Visual change detected - VLM analysis unavailable",
        "confidence": 0.5,
        "action_category": "menu"
    }
