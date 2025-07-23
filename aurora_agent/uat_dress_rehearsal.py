"""
UAT Dress Rehearsal Setup Script for Aurora Agent Platform
Complete end-to-end testing of teacher and student workflows
"""
import asyncio
import logging
import os
from pathlib import Path

# Setup logging for UAT
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('uat_dress_rehearsal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UATDressRehearsal:
    """Complete UAT test coordinator for Aurora Agent platform."""
    
    def __init__(self):
        self.test_results = {
            "environment_setup": False,
            "database_ready": False,
            "teacher_workflow": False,
            "student_workflow": False,
            "integration_test": False
        }
        
    async def run_complete_uat(self):
        """Execute the complete dress rehearsal UAT."""
        logger.info("🎭 Starting Aurora Agent Dress Rehearsal UAT")
        logger.info("=" * 60)
        
        try:
            # Phase 1: Environment Setup
            await self.setup_test_environment()
            
            # Phase 2: Database Preparation
            await self.prepare_database()
            
            # Phase 3: Service Validation
            await self.validate_services()
            
            # Phase 4: Generate Test Instructions
            await self.generate_test_instructions()
            
            # Phase 5: Summary
            self.print_uat_summary()
            
        except Exception as e:
            logger.error(f"UAT failed: {e}", exc_info=True)
            return False
        
        return True
    
    async def setup_test_environment(self):
        """Setup the test environment for UAT."""
        logger.info("🔧 Setting up test environment...")
        
        # Check required files exist
        required_files = [
            "app_simple.py",
            "session_core.py",
            "student_verifier.py",
            "langgraph_coaching_nodes.py",
            "static/lesson-builder.html",
            "static/lesson-builder.js",
            "models/lesson.py",
            "api/lessons.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"❌ Missing required files: {missing_files}")
            return False
        
        logger.info("✅ All required files present")
        
        # Check environment variables
        required_env_vars = [
            "GEMINI_API_KEY",
            "GOOGLE_SERVICE_ACCOUNT_KEY_PATH",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET"
        ]
        
        missing_env_vars = []
        for env_var in required_env_vars:
            if not os.getenv(env_var):
                missing_env_vars.append(env_var)
        
        if missing_env_vars:
            logger.warning(f"⚠️ Missing environment variables: {missing_env_vars}")
            logger.info("UAT can continue but some features may not work")
        else:
            logger.info("✅ All environment variables present")
        
        self.test_results["environment_setup"] = True
        return True
    
    async def prepare_database(self):
        """Initialize database for UAT."""
        logger.info("🗄️ Preparing database for UAT...")
        
        try:
            # Import and run database initialization
            from init_db import init_database
            init_database()
            
            logger.info("✅ Database initialized successfully")
            self.test_results["database_ready"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    async def validate_services(self):
        """Validate that all services can be imported and initialized."""
        logger.info("🔍 Validating services...")
        
        try:
            # Test SessionCore
            from session_core import SessionCore
            logger.info("✅ SessionCore imported successfully")
            
            # Test Student Verifier
            from student_verifier import await_and_verify_student_action, student_subscriber
            logger.info("✅ Student Verifier imported successfully")
            
            # Test LangGraph Coaching
            from langgraph_coaching_nodes import create_coaching_graph, start_coaching_session
            coaching_graph = create_coaching_graph()
            logger.info("✅ LangGraph Coaching Graph created successfully")
            
            # Test Lesson API
            from api.lessons import router as lesson_router
            logger.info("✅ Lesson API imported successfully")
            
            # Test VLM Differ
            from vlm_differ import analyze_image_diff
            logger.info("✅ VLM Differ imported successfully")
            
            # Test Sheets Tool
            from tools.sheets import get_sheets_tool_instance
            sheets_tool = get_sheets_tool_instance()
            logger.info("✅ Sheets Tool initialized successfully")
            
            logger.info("✅ All services validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Service validation failed: {e}", exc_info=True)
            return False
    
    async def generate_test_instructions(self):
        """Generate detailed test instructions for manual UAT."""
        logger.info("📋 Generating test instructions...")
        
        instructions = """
🎭 AURORA AGENT DRESS REHEARSAL - COMPLETE UAT INSTRUCTIONS
===========================================================

ENVIRONMENT SETUP:
1. Start the FastAPI backend:
   cd /Users/arastu/Desktop/session-bubble/aurora_agent
   python -m uvicorn app_simple:app --reload --port 8000

2. Open TWO browser windows:
   - Window 1 (Teacher): http://localhost:8000/static/lesson-builder.html
   - Window 2 (Student): http://localhost:8000/static/lesson-builder.html

3. Prepare a clean Google Sheet for testing

PART 1: TEACHER EXPERIENCE (LESSON CREATION)
============================================

Step 1.1 - Start Imprinting Session:
- In Teacher browser, click "Connect to Verification Session"
- Enter your test Google Sheet URL
- Click "Start Session"
- EXPECTED: Remote browser opens with Google Sheet
- EXPECTED: Live Action Log shows "Session connected"

Step 1.2 - Imprint Action 1 (Write Cell):
- In Remote browser: Click cell A1
- Type "Sales Data" and press Enter
- EXPECTED: Live Action Log shows VERIFIED_ACTION
- EXPECTED: Action shows "write_cell" with verification status

Step 1.3 - Add to Lesson:
- Click "[Add to Lesson]" button for the write action
- EXPECTED: Action appears in Final Lesson Plan panel
- EXPECTED: Step shows narration field (editable)

Step 1.4 - Imprint Action 2 (Format Bold):
- In Remote browser: Select cell A1
- Click Bold button in toolbar (or Ctrl+B)
- EXPECTED: Live Action Log shows new VERIFIED_ACTION
- EXPECTED: Action shows formatting verification

Step 1.5 - Add to Lesson:
- Click "[Add to Lesson]" for the bold action
- EXPECTED: Second step appears in lesson plan

Step 1.6 - Save Lesson:
- Enter lesson title: "Intro to Formatting"
- Click "Save Lesson"
- EXPECTED: Success message appears
- EXPECTED: Lesson saved to database

PART 2: STUDENT EXPERIENCE (AI COACHING)
========================================

Step 2.1 - Load Lesson for Coaching:
- In Student browser, load the saved lesson
- Start coaching session
- EXPECTED: AI coach begins with demonstration

Step 2.2 - AI Demonstration:
- EXPECTED: AI shows "Let me demonstrate step 1..."
- EXPECTED: Coaching interface shows current step

Step 2.3 - Student Attempt:
- Student tries to click A1 and type "Sales Data"
- EXPECTED: Verification system captures action
- EXPECTED: AI coach provides feedback

Step 2.4 - Progress Through Lesson:
- Continue through all lesson steps
- EXPECTED: AI adapts based on student success/failure
- EXPECTED: Lesson completes successfully

SUCCESS CRITERIA:
================
✅ Real-time action capture and verification
✅ Lesson creation and persistence
✅ AI coaching with adaptive feedback
✅ WebSocket communication working
✅ All three workstreams integrated
✅ End-to-end teacher-student workflow

TROUBLESHOOTING:
===============
- Check browser console for errors
- Check server logs for verification issues
- Ensure Google OAuth is properly configured
- Verify environment variables are set
- Check database connectivity

LOG FILES:
==========
- Server logs: Check terminal output
- UAT logs: uat_dress_rehearsal.log
- Browser logs: F12 Developer Tools
        """
        
        # Write instructions to file
        with open("UAT_INSTRUCTIONS.md", "w") as f:
            f.write(instructions)
        
        logger.info("✅ Test instructions generated: UAT_INSTRUCTIONS.md")
        return True
    
    def print_uat_summary(self):
        """Print UAT setup summary."""
        logger.info("🎭 UAT DRESS REHEARSAL SETUP COMPLETE")
        logger.info("=" * 50)
        
        for test_name, passed in self.test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        
        logger.info("=" * 50)
        logger.info("📋 Next Steps:")
        logger.info("1. Review UAT_INSTRUCTIONS.md")
        logger.info("2. Start the FastAPI server")
        logger.info("3. Open two browser windows")
        logger.info("4. Execute the dress rehearsal script")
        logger.info("5. Validate all success criteria")
        logger.info("=" * 50)

async def main():
    """Run the complete UAT setup."""
    uat = UATDressRehearsal()
    success = await uat.run_complete_uat()
    
    if success:
        print("\n🎉 UAT SETUP SUCCESSFUL! Ready for dress rehearsal.")
        print("📋 See UAT_INSTRUCTIONS.md for detailed test steps.")
    else:
        print("\n❌ UAT SETUP FAILED! Check logs for issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
