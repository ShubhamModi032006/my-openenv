from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any, Dict
from env.email_env import EmailTriageEnv
from env.models import Action
import uuid
import time

app = FastAPI(title="Email Triage OpenEnv API")

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Email Triage OpenEnv API!",
        "status": "online",
        "instructions": "Send POST requests to /reset and /step to interact with the environment."
    }

SESSIONS: Dict[str, Dict[str, Any]] = {}

class ResetRequest(BaseModel):
    task_level: Optional[str] = None

class StepRequest(BaseModel):
    session_id: str
    action: Action

@app.post("/reset")
def reset(req: Optional[ResetRequest] = None):
    try:
        task_level = req.task_level if req else None
        env = EmailTriageEnv(task_level=task_level if task_level else "easy")
        obs = env.reset()
        
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {
            "env": env,
            "last_accessed": time.time()
        }
        
        return {
            "session_id": session_id,
            "observation": obs.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step")
def step(req: StepRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found or expired")
        
    session_data = SESSIONS[req.session_id]
    session_data["last_accessed"] = time.time()
    env = session_data["env"]
    
    try:
        obs, reward, done, info = env.step(req.action)
        return {
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state")
def state(session_id: str = Query(..., description="The session ID returned from /reset")):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
        
    env = SESSIONS[session_id]["env"]
    return env.state()

@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        return {"status": "success", "message": f"Session {session_id} deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
