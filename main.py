from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import json
from typing import Dict, List

app = FastAPI()

rooms: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    rooms.setdefault(room_id, []).append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Рассылаем сообщение всем в комнате (кроме отправителя)
            for ws in rooms[room_id]:
                if ws != websocket:
                    await ws.send_text(data)
    except WebSocketDisconnect:
        rooms[room_id].remove(websocket)
        if not rooms[room_id]:
            del rooms[room_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)