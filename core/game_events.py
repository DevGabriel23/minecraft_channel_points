# core/game_events.py
import convert_case
from typing import Any, Awaitable, Callable
from bedrock.context import GameContext, PlayerTransformContext, PlayerMessageContext
from bedrock.events import GameEvent

from core.state import game_event_handlers, player_data
from core.custom_commands import parse_and_execute_command

def game_event(fn: Callable[[GameContext], Awaitable[Any]]) -> GameEvent:
    event_name = fn.__name__.replace('_', ' ')
    event_name = convert_case.pascal_case(event_name)
    event = GameEvent(event_name, fn)
    game_event_handlers.append(event)
    return event

@game_event
async def player_transform(ctx: PlayerTransformContext):
    """Se dispara cuando la posición o rotación del jugador cambia."""
    player_name = ctx.player
    player_pos = ctx.player_position
    
    if player_name not in player_data:
        player_data[player_name] = {}
    
    # Actualiza los datos de posición y rotación sin sobrescribir
    player_data[player_name]["position"] = {
        "x": player_pos[0].coord, 
        "y": player_pos[1].coord, 
        "z": player_pos[2].coord
    }
    
    player_data[player_name]["rotation"] = ctx._data.get('player', {}).get("yRot", 0)

@game_event
async def player_join(ctx: GameContext):
    """Se dispara cuando un jugador se une."""
    # En este caso, el evento player_join no tiene una clase de contexto específica,
    # así que usamos la clase base GameContext para acceder a los datos.
    player_name = ctx.data.get("player", {}).get("name")
    if player_name:
        player_data[player_name] = {"position": None}
        print(f"El jugador {player_name} se ha unido al mundo.")

@game_event
async def player_message(ctx: PlayerMessageContext):
    """Se dispara cuando un jugador envía un mensaje."""
    sender = ctx.sender
    message = ctx.message
    
    if sender in ["External", "Externo", ""]:
        # print(f"Ignorando mensaje del sistema: {message}") # Descomentar para depuración
        return

    if message.startswith('!'):
        await parse_and_execute_command(message, sender)

    print(f"El jugador {sender} ha enviado un mensaje: {message}")
