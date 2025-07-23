
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
        