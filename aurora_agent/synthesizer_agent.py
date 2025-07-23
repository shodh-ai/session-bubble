"""
Layer 3: ANALYSIS - Synthesizer Agent (Fusion Engine)
Triple-Verified Architecture Implementation

This module implements the third layer of the Triple-Verified Architecture:
- Receives complete data bundle from Layer 2 (Triage)
- Runs VLM differ and API differ in parallel
- Synthesizes all evidence via LLM into final VERIFIED_ACTION
- True "fusion engine" combining multiple imperfect data streams
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import existing tools
from vlm_differ import analyze_image_diff

logger = logging.getLogger(__name__)

@dataclass
class EvidenceBundle:
    """Structured representation of evidence from Layer 2."""
    raw_event: Dict[str, Any]
    before_screenshot: Optional[bytes]
    after_screenshot: Optional[bytes]
    before_api_state: Optional[Dict[str, Any]]
    after_api_state: Optional[Dict[str, Any]]
    timestamp: float

class APIStateDiffer:
    """
    Tool 2: API Differ
    Compares before/after API snapshots and returns description of data changes.
    """
    
    @staticmethod
    def compare_api_states(before_state: Optional[Dict[str, Any]], 
                          after_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare two API snapshots and return a structured diff.
        
        This is the simple Python function that replaces complex API verification.
        """
        try:
            if not before_state or not after_state:
                return {
                    "has_changes": False,
                    "description": "No API state available for comparison",
                    "confidence": 0.0,
                    "changes": []
                }
            
            changes = []
            
            # Compare data changes (simplified for now)
            before_data = before_state.get("spreadsheet_data", {})
            after_data = after_state.get("spreadsheet_data", {})
            
            if before_data != after_data:
                changes.append({
                    "type": "data_change",
                    "description": "Spreadsheet data modified",
                    "before": str(before_data)[:100],  # First 100 chars
                    "after": str(after_data)[:100]
                })
            
            # Compare formatting changes
            before_format = before_state.get("formatting_info", {})
            after_format = after_state.get("formatting_info", {})
            
            if before_format != after_format:
                changes.append({
                    "type": "formatting_change", 
                    "description": "Cell formatting modified",
                    "before": str(before_format)[:100],
                    "after": str(after_format)[:100]
                })
            
            # Determine overall change assessment
            has_changes = len(changes) > 0
            confidence = 0.95 if has_changes else 0.8  # High confidence in API data
            
            description = "No changes detected"
            if changes:
                change_types = [c["type"] for c in changes]
                description = f"API detected: {', '.join(change_types)}"
            
            return {
                "has_changes": has_changes,
                "description": description,
                "confidence": confidence,
                "changes": changes,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error in API differ: {e}")
            return {
                "has_changes": False,
                "description": f"API diff error: {str(e)}",
                "confidence": 0.0,
                "changes": [],
                "error": str(e)
            }

class SynthesizerAgent:
    """
    Layer 3: ANALYSIS - The Fusion Engine
    
    Intelligently combines multiple imperfect data streams:
    1. Raw Playwright event (precise but limited context)
    2. VLM analysis (visual understanding but can be inaccurate)  
    3. API diff (reliable data changes but misses visual changes)
    
    Produces final, high-confidence VERIFIED_ACTION.
    """
    
    def __init__(self):
        self.api_differ = APIStateDiffer()
        
    async def synthesize_action(self, data_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main synthesis function - the heart of the fusion engine.
        
        Takes data bundle from Layer 2 and produces VERIFIED_ACTION.
        """
        try:
            logger.info("🧠 Layer 3 ANALYSIS: Starting evidence synthesis")
            
            # Parse the data bundle
            evidence = self._parse_data_bundle(data_bundle)
            
            # Run parallel analysis (Tool 1 & Tool 2)
            vlm_result, api_result = await self._run_parallel_analysis(evidence)
            
            # Synthesize all evidence via LLM
            verified_action = await self._synthesize_with_llm(
                evidence.raw_event, vlm_result, api_result
            )
            
            logger.info(f"✅ Layer 3 ANALYSIS: Synthesis complete - {verified_action.get('tool_name')}")
            return verified_action
            
        except Exception as e:
            logger.error(f"Error in synthesizer agent: {e}", exc_info=True)
            return self._create_error_action(str(e))
    
    def _parse_data_bundle(self, data_bundle: Dict[str, Any]) -> EvidenceBundle:
        """Parse the data bundle from Layer 2 into structured evidence."""
        
        # Convert hex strings back to bytes for screenshots
        before_screenshot = None
        after_screenshot = None
        
        if data_bundle.get("before_screenshot_bytes"):
            before_screenshot = bytes.fromhex(data_bundle["before_screenshot_bytes"])
        if data_bundle.get("after_screenshot_bytes"):
            after_screenshot = bytes.fromhex(data_bundle["after_screenshot_bytes"])
        
        return EvidenceBundle(
            raw_event=data_bundle.get("raw_playwright_event", {}),
            before_screenshot=before_screenshot,
            after_screenshot=after_screenshot,
            before_api_state=data_bundle.get("before_api_snapshot"),
            after_api_state=data_bundle.get("after_api_snapshot"),
            timestamp=data_bundle.get("timestamp", time.time())
        )
    
    async def _run_parallel_analysis(self, evidence: EvidenceBundle) -> tuple:
        """
        Run Tool 1 (VLM differ) and Tool 2 (API differ) in parallel.
        
        This is the core of the fusion approach - multiple analysis streams.
        """
        try:
            tasks = [
                # Tool 1: VLM Analysis
                self._run_vlm_analysis(evidence.before_screenshot, evidence.after_screenshot),
                # Tool 2: API Diff Analysis  
                self._run_api_analysis(evidence.before_api_state, evidence.after_api_state)
            ]
            
            vlm_result, api_result = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions from parallel tasks
            if isinstance(vlm_result, Exception):
                logger.error(f"VLM analysis failed: {vlm_result}")
                vlm_result = {"error": str(vlm_result), "description": "VLM analysis failed"}
            
            if isinstance(api_result, Exception):
                logger.error(f"API analysis failed: {api_result}")
                api_result = {"error": str(api_result), "description": "API analysis failed"}
            
            return vlm_result, api_result
            
        except Exception as e:
            logger.error(f"Error in parallel analysis: {e}")
            return {"error": str(e)}, {"error": str(e)}
    
    async def _run_vlm_analysis(self, before_screenshot: Optional[bytes], 
                               after_screenshot: Optional[bytes]) -> Dict[str, Any]:
        """Tool 1: Run VLM differ analysis."""
        try:
            if not before_screenshot or not after_screenshot:
                return {
                    "description": "No screenshots available for VLM analysis",
                    "confidence": 0.0,
                    "tool_name": "vlm_unavailable"
                }
            
            # Use existing VLM differ
            vlm_result = await analyze_image_diff(before_screenshot, after_screenshot)
            
            logger.info(f"🔍 VLM analysis: {vlm_result.get('tool_name', 'unknown')}")
            return vlm_result
            
        except Exception as e:
            logger.error(f"VLM analysis error: {e}")
            return {
                "description": f"VLM analysis error: {str(e)}",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _run_api_analysis(self, before_state: Optional[Dict[str, Any]], 
                               after_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Tool 2: Run API differ analysis."""
        try:
            # Use the simple API differ
            api_result = self.api_differ.compare_api_states(before_state, after_state)
            
            logger.info(f"📊 API analysis: {api_result.get('description', 'unknown')}")
            return api_result
            
        except Exception as e:
            logger.error(f"API analysis error: {e}")
            return {
                "description": f"API analysis error: {str(e)}",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _synthesize_with_llm(self, raw_event: Dict[str, Any], 
                                  vlm_result: Dict[str, Any], 
                                  api_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Final LLM synthesis of all three evidence sources.
        
        This is where the magic happens - intelligent fusion of multiple data streams.
        """
        try:
            # Prepare synthesis prompt
            synthesis_prompt = self._create_synthesis_prompt(raw_event, vlm_result, api_result)
            
            # For now, create a rule-based synthesis
            # In full implementation, this would call an LLM
            verified_action = self._rule_based_synthesis(raw_event, vlm_result, api_result)
            
            return verified_action
            
        except Exception as e:
            logger.error(f"LLM synthesis error: {e}")
            return self._create_error_action(str(e))
    
    def _create_synthesis_prompt(self, raw_event: Dict[str, Any], 
                                vlm_result: Dict[str, Any], 
                                api_result: Dict[str, Any]) -> str:
        """Create the synthesis prompt for the LLM."""
        
        prompt = f"""
        Synthesize these three data points into a single, high-confidence action:

        **Evidence 1 - Raw Playwright Event:**
        - Type: {raw_event.get('type', 'unknown')}
        - Target: {raw_event.get('target', 'unknown')}
        - Coordinates: ({raw_event.get('x', 0)}, {raw_event.get('y', 0)})
        - ARIA Label: {raw_event.get('aria_label', 'none')}

        **Evidence 2 - VLM Analysis:**
        - Description: {vlm_result.get('description', 'unavailable')}
        - Tool Name: {vlm_result.get('tool_name', 'unknown')}
        - Confidence: {vlm_result.get('confidence', 0.0)}

        **Evidence 3 - API Diff:**
        - Changes Detected: {api_result.get('has_changes', False)}
        - Description: {api_result.get('description', 'unavailable')}
        - Confidence: {api_result.get('confidence', 0.0)}

        Based on this evidence, determine the most likely user action and create a VERIFIED_ACTION JSON object.
        """
        
        return prompt
    
    def _rule_based_synthesis(self, raw_event: Dict[str, Any], 
                             vlm_result: Dict[str, Any], 
                             api_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule-based synthesis (temporary implementation).
        
        This will be replaced by LLM synthesis in the full implementation.
        """
        
        # Determine the most reliable evidence source
        vlm_confidence = vlm_result.get('confidence', 0.0)
        api_confidence = api_result.get('confidence', 0.0)
        
        # Synthesis logic
        if api_result.get('has_changes', False) and api_confidence > 0.8:
            # API detected changes - high confidence
            primary_source = "api"
            description = f"Data change: {api_result.get('description', 'unknown')}"
            tool_name = "sheets_data_modification"
            confidence = api_confidence
            
        elif vlm_confidence > 0.7:
            # VLM analysis available - medium confidence
            primary_source = "vlm"
            description = vlm_result.get('description', 'Visual change detected')
            tool_name = vlm_result.get('tool_name', 'visual_interaction')
            confidence = vlm_confidence
            
        else:
            # Fall back to raw event - basic confidence
            primary_source = "playwright"
            description = f"UI interaction: {raw_event.get('type')} on {raw_event.get('target', 'element')}"
            tool_name = "ui_interaction"
            confidence = 0.6
        
        # Create synthesized verified action
        verified_action = {
            "type": "VERIFIED_ACTION",
            "interpretation": description,
            "verification": f"Synthesized from {primary_source} evidence (confidence: {confidence:.2f})",
            "status": "SUCCESS",
            "tool_name": tool_name,
            "parameters": {
                "event_type": raw_event.get("type"),
                "coordinates": {
                    "x": raw_event.get("x", 0),
                    "y": raw_event.get("y", 0)
                },
                "target": raw_event.get("target", "unknown"),
                "aria_label": raw_event.get("aria_label", ""),
                "synthesis_method": primary_source
            },
            "confidence": confidence,
            "timestamp": time.time(),
            "architecture": "triple_verified_synthesis",
            "evidence_summary": {
                "playwright": {
                    "type": raw_event.get("type"),
                    "target": raw_event.get("target")
                },
                "vlm": {
                    "description": vlm_result.get("description", "unavailable"),
                    "confidence": vlm_confidence
                },
                "api": {
                    "has_changes": api_result.get("has_changes", False),
                    "confidence": api_confidence
                }
            }
        }
        
        return verified_action
    
    def _create_error_action(self, error_message: str) -> Dict[str, Any]:
        """Create an error VERIFIED_ACTION when synthesis fails."""
        return {
            "type": "VERIFIED_ACTION",
            "interpretation": "Analysis error occurred",
            "verification": f"Synthesis failed: {error_message}",
            "status": "ERROR",
            "tool_name": "synthesis_error",
            "parameters": {"error": error_message},
            "confidence": 0.0,
            "timestamp": time.time(),
            "architecture": "triple_verified_synthesis"
        }

# Global synthesizer instance
synthesizer_agent = SynthesizerAgent()

async def synthesize_data_bundle(data_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Layer 3 synthesis.
    
    Called by Layer 2 (SessionCore) to process data bundles.
    """
    return await synthesizer_agent.synthesize_action(data_bundle)
