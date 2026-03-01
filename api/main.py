import sys
import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import run_agent, run_agent_stream
from src.conversation_manager import ConversationManager

app = FastAPI(title="InsightX API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"

# Simple in-memory storage for session context
sessions: Dict[str, ConversationManager] = {}

def get_session(session_id: str) -> ConversationManager:
    if session_id not in sessions:
        sessions[session_id] = ConversationManager()
    return sessions[session_id]

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/query_stream")
async def process_query_stream(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    session_id = req.session_id or "default"
    cm = get_session(session_id)
    context = cm.get_context()

    def event_generator():
        try:
            # We must run the generator and yield its events formatted for SSE
            # run_agent_stream yields JSON strings.
            # We add the SSE format "data: <json>\n\n"
            final_response = None
            final_result = None
            final_code = ""

            for event_json in run_agent_stream(req.query, conversation_context=context):
                yield f"data: {event_json}\n\n"
                
                # Try to parse the event to capture final data for history
                try:
                    event_data = json.loads(event_json)
                    if event_data.get("type") == "final":
                        payload = event_data.get("data", {})
                        final_response = payload.get("response", "")
                        final_result = payload.get("result", {})
                        final_code = payload.get("code", "")
                except Exception:
                    pass

            # After yielding all events, save to conversation history
            if final_response and final_result is not None:
                cm.add_turn(
                    user_query=req.query,
                    parsed_intent={},
                    analytics_result=final_result,
                    insight_response=final_response,
                    code=final_code,
                    result_summary=final_result.get("summary", "") if isinstance(final_result, dict) else "",
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_json = json.dumps({
                "type": "error",
                "data": {"message": f"Server Error: {str(e)}"}
            })
            yield f"data: {error_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/query")
def process_query(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    session_id = req.session_id or "default"
    cm = get_session(session_id)
    context = cm.get_context()
    
    try:
        agent_result = run_agent(req.query, conversation_context=context)
        
        # Add to conversation history
        response = agent_result["response"]
        result = agent_result["result"]
        
        cm.add_turn(
            user_query=req.query,
            parsed_intent={},
            analytics_result=result,
            insight_response=response,
            code=agent_result.get("code", ""),
            result_summary=result.get("summary", "") if isinstance(result, dict) else "",
        )
        
        return {
            "response": response,
            "result": result,
            "followups": agent_result.get("followups", []),
            "mode": agent_result.get("mode", "code_interpreter"),
            "steps": agent_result.get("steps", []),
            "code": agent_result.get("code", ""),
            "verdict": agent_result.get("verdict", {})
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8080, reload=True)
