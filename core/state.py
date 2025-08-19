# core/state.py
import asyncio
from typing import Dict, List
from fastapi import WebSocket
from bedrock.events import GameEvent

# Variables Globales
player_data: Dict[str, Dict] = {}
active_connections: List[WebSocket] = []
command_requests: Dict[str, asyncio.Future] = {}
game_event_handlers: List[GameEvent] = []