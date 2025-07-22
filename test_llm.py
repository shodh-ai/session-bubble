# in /session-bubble/test_llm_call.py
import asyncio
import os
from dotenv import load_dotenv
import google.generativeai as genai

async def main():
    print("--- LLM ISOLATION TEST ---")
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found!")
        return
        
    print("API Key found. Configuring GenAI...")
    genai.configure(api_key=api_key)
    
    try:
        print("Creating GenerativeModel...")
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        print("Calling generate_content_async...")
        # Use a timeout to prevent waiting forever
        response = await asyncio.wait_for(
            model.generate_content_async("What is 1+1?"),
            timeout=10.0 # Wait a maximum of 10 seconds
        )
        
        print("\n--- SUCCESS! ---")
        print(f"LLM Response: {response.text}")
        
    except asyncio.TimeoutError:
        print("\n--- FAILURE! ---")
        print("The API call timed out after 10 seconds.")
    except Exception as e:
        print(f"\n--- FAILURE! ---")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())