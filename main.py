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
PORT = os.getenv('PORT',default=8001)
print(PROTOKOL,DOMAIN)
print("PORT",PORT)

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

users = {}
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



@app.websocket("/users/{username}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    username: str,
    q: Union[int, None] = None,
    cookie_or_token: str = Depends(get_cookie_or_token),
):
    
    client_id = cookie_or_token
    manager = users.get(username)
    if manager == None:
        manager = ConnectionManager()
        users[username] = manager
    print("Connecting ", username)
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await users.get(username).send_personal_message(f"You wrote: {data}", websocket)
            await users.get(username).broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        print("Disconnecting: ", username, client_id)
        users.get(username).disconnect(websocket)
        await users.get(username).broadcast(f"Client #{client_id} left the chat")


@app.post("/message")
async def message(m = Body()):
    usrs = m.get("users")
    # print(usrs)
    seconds = str(time.time())
    found = False
    for username in usrs:
        manager = users.get(username)
        if manager == None:
            continue
        found = True
        await manager.broadcast(seconds)

    if not found:
        return JSONResponse(content={"message": "Nobody is listening"}, 
                            status_code=status.HTTP_404_NOT_FOUND)
    return HTMLResponse(status_code=status.HTTP_201_CREATED)
    




