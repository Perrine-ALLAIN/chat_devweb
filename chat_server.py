from collections import deque
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI()

messages = deque(maxlen=128)

class ChatMessage(BaseModel):
    name: str
    message: str

chat_html = Path("./chat.html").read_text(encoding="utf-8")

@app.get("/chat", response_class=HTMLResponse)
async def chat():
    return chat_h

@app.get("/poll")
async def poll():
    return JSONResponse({"messages": list(messages)})

@app.post("/send")
async def send(msg: ChatMessage):
    messages.append({
        "name": msg.name,
        "message": msg.message,
    })
    return {"ok": True}
