# main.py
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api import websocket
from api import routes
from core.state import active_connections, command_requests, player_data, game_event_handlers

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir las rutas de la API y los endpoints de WebSocket
app.include_router(routes.router)
app.add_api_websocket_route("/ws", websocket.websocket_endpoint)