# in aurora_agent/tools/jupyter/notebook_parser_tool.py
import logging
import json
import nbformat
from aurora_agent.browser_manager import browser_manager
    
logger = logging.getLogger(__name__)

async def get_notebook_state() -> str:
    """
    Gets the entire state of the active Jupyter Notebook as a structured JSON object.
    This is the most reliable way to read the content and output of all cells.
    """
    logger.info("--- TOOL: Getting full notebook state with nbformat ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."

    try:
        # This JavaScript finds the main JupyterLab application object,
        # gets the active notebook widget, and asks for its data model.
        notebook_json = await page.evaluate("""
            () => {
                const notebookPanel = window.jupyterapp.shell.currentWidget;
                if (notebookPanel && notebookPanel.content && notebookPanel.content.model) {
                    return notebookPanel.content.model.toJSON();
                }
                return null;
            }
        """)

        if not notebook_json:
            return "Error: Could not find an active Jupyter notebook on the page."

        # The data is now a standard .ipynb JSON structure.
        # We can parse it to create a clean, human-readable summary for the agent.
        notebook = nbformat.reads(json.dumps(notebook_json), as_version=4)
        
        summary = []
        for i, cell in enumerate(notebook.cells):
            cell_summary = {
                "cell_index": i,
                "cell_type": cell.cell_type,
                "source": cell.source,
                "outputs": []
            }
            if 'outputs' in cell:
                for output in cell.outputs:
                    if output.output_type == 'stream':
                        cell_summary["outputs"].append({"type": "text", "content": output.text})
                    elif output.output_type == 'error':
                        cell_summary["outputs"].append({"type": "error", "content": f"{output.ename}: {output.evalue}"})
                    elif output.output_type == 'display_data' and 'data' in output:
                        if 'text/plain' in output.data:
                             cell_summary["outputs"].append({"type": "text", "content": output.data['text/plain']})
                        elif 'image/png' in output.data:
                             cell_summary["outputs"].append({"type": "image", "content": "An image was generated."})
            summary.append(cell_summary)

        return json.dumps(summary)

    except Exception as e:
        logger.error(f"Failed to get notebook state: {e}", exc_info=True)
        return f"Error: An exception occurred while getting notebook state: {e}"