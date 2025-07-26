# File: session-bubble/record_script.py
# in /session-bubble/record_script.py (FINAL, WORKING VERSION)
import subprocess
import os
import ast
import argparse
import sys

# Define the target directory for the cleaned scripts
SCRIPTS_DIR = os.path.join('aurora_agent', 'recorded_scripts')
TEMP_FILE = "_temp_recorded_script.py"
AUTH_FILE = "auth.json"

def run_codegen(url: str):
    """
    Runs the Playwright codegen process, instructing it to generate
    ASYNC code directly.
    """
    if not os.path.exists(AUTH_FILE):
        print(f"ERROR: Authentication file not found at '{AUTH_FILE}'.")
        print("Please run 'python setup_auth.py' first.")
        sys.exit(1)

    print("\n" + "="*50)
    print("🚀 Starting Playwright ASYNC Recording Session...")
    print("✅ Perform your actions in the browser window.")
    print("🔴 When you are finished, CLOSE the browser window.")
    print("="*50 + "\n")

    # Use the '--target python-async' flag to get the correct code format.
    command = [
        "playwright", "codegen",
        "--target", "python-async",
        "--load-storage", AUTH_FILE,
        "-o", TEMP_FILE,
        url
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("✅ Recording session finished.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Codegen process failed. It might be because the browser was closed too quickly.")
        print(f"   Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"\n❌ An unexpected error occurred during codegen: {e}")
        return False

def sanitize_script(output_filename: str):
    """
    Reads the raw async script and extracts only the relevant action lines
    from the 'run' function body.
    """
    if not os.path.exists(TEMP_FILE):
        print(f"❌ Error: Temporary file '{TEMP_FILE}' not found.")
        return

    print(f"🔬 Sanitizing the recorded script...")
    with open(TEMP_FILE, 'r') as f:
        source_code = f.read()
    
    if not source_code.strip():
        print("❌ Error: The recorded script is empty.")
        os.remove(TEMP_FILE)
        return

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        print(f"❌ Error: Failed to parse the recorded code: {e}")
        return

    # --- THIS IS THE FINAL FIX ---
    # We now correctly look for the `async def run` function.
    run_function_body = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == 'run':
            # --- THIS IS THE REFINEMENT ---
            # We slice to remove setup/teardown AND filter out unwanted lines
            body_nodes = node.body[3:-2] 
            
            # Filter out any 'page.goto' or 'page.close' calls
            filtered_body = [
                n for n in body_nodes 
                if not (isinstance(n, ast.Expr) and 
                        isinstance(n.value, ast.Await) and
                        isinstance(n.value.value, ast.Call) and
                        isinstance(n.value.value.func, ast.Attribute) and
                        n.value.value.func.attr in ['goto', 'close'])
            ]
            run_function_body = filtered_body
            break
            
    if not run_function_body:
        print("❌ Error: Could not find a valid 'async def run(...)' function body in the recorded script.")
        print(f"   Please inspect the temporary file for issues: {os.path.abspath(TEMP_FILE)}")
        return
    # --- END OF FIX ---

    clean_code = ast.unparse(run_function_body)
    
    final_script_content = (
        f"# Recorded actions for: {output_filename}\n\n"
        f"{clean_code}"
    )
    
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    final_path = os.path.join(SCRIPTS_DIR, f"{output_filename}.py")

    with open(final_path, 'w') as f:
        f.write(final_script_content)

    os.remove(TEMP_FILE)
    print(f"✅ Successfully saved clean ASYNC script to: {final_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A utility to record and sanitize Playwright scripts.")
    parser.add_argument("--name", required=True, help="The name of the script file to create.")
    parser.add_argument("--url", required=True, help="The starting URL for the recording session.")
    args = parser.parse_args()

    if run_codegen(args.url):
        sanitize_script(args.name)