from typing import List, Union
import os
import time


from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import (
    Body,
    Cookie,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    status,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)

app = FastAPI()

PROTOKOL = os.getenv("PROTOKOL",default="ws://")
DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN",default="localhost:8001")
print(PROTOKOL,DOMAIN)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`"""+PROTOKOL+DOMAIN+"""/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

pubs = {}
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


# manager = ConnectionManager()


@app.get("/")
async def get():
    # return HTMLResponse(html)
    return {"messsage": "Hello"}

async def get_cookie_or_token(
    websocket: WebSocket,
    session: Union[str, None] = Cookie(default=None),
    token: Union[str, None] = Query(default=None),
):
    if session is None and token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return session or token



@app.websocket("/pubs/{pub_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    pub_id: str,
    q: Union[int, None] = None,
    cookie_or_token: str = Depends(get_cookie_or_token),
):
    
    client_id = cookie_or_token
    manager = pubs.get(pub_id)
    if manager == None:
        manager = ConnectionManager()
        pubs[pub_id] = manager
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await pubs.get(pub_id).send_personal_message(f"You wrote: {data}", websocket)
            await pubs.get(pub_id).broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        pubs.get(pub_id).disconnect(websocket)
        await pubs.get(pub_id).broadcast(f"Client #{client_id} left the chat")

class Message:
    pub_id: str
    message: str


@app.post("/message")
async def message(m = Body()):
    pub_id = m.get("pub_id")
    print(m)
    print(pub_id)
    manager = pubs.get(pub_id)
    if manager == None:
        raise HTTPException(status_code=404, detail='Item not found')
    seconds = str(time.time())
    await manager.broadcast(seconds)
    return seconds
    




