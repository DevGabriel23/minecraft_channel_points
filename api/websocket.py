# api/websocket.py
import json
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from core.state import active_connections, command_requests
from core.game_events import game_event_handlers
from bedrock.response import CommandResponse
from bedrock.context import get_game_context
import convert_case
from core.commands import FakeServer

fake_bedrock_server = FakeServer()

# Lógica para registrar eventos
async def register_event_listeners(websocket: WebSocket):
    """Registra los eventos en el cliente de Minecraft al conectarse."""
    for event in game_event_handlers:
        command_payload = {
            "header": {
                "version": 1,
                "requestId": str(uuid.uuid4()),
                "messagePurpose": "subscribe",
                "messageType": "commandRequest"
            },
            "body": {
                "eventName": event.name,
            },
        }
        await websocket.send_text(json.dumps(command_payload))

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print(f"Nuevo cliente de Minecraft conectado: {websocket.client}")

    await register_event_listeners(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            header = message.get("header", {})
            message_purpose = header.get("messagePurpose")
            
            if message_purpose == "commandResponse":
                request_id = header.get("requestId")
                if request_id in command_requests:
                    future = command_requests.pop(request_id)
                    response_obj = CommandResponse.parse(message)
                    future.set_result(response_obj)
            elif message_purpose == "event":
                event_name = header.get("eventName")
                event_body = message.get("body", {})

                if event_name:
                    try:
                        # Usamos la función de BedrockPy para obtener la clase de contexto correcta
                        name = convert_case.snake_case(event_name)
                        ContextClass = get_game_context(name)
                        ctx = ContextClass(fake_bedrock_server, event_body)
                        
                        # Buscamos y disparamos el handler registrado
                        for event in game_event_handlers:
                            if event.name == event_name:
                                await event(ctx)

                    except KeyError:
                        # Manejo de eventos no registrados
                        print(f"Evento no manejado: {event_name}")
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"Cliente de Minecraft desconectado.")
    except Exception as e:
        print(f"Error en la conexión WebSocket: {e}: {str(e)}")