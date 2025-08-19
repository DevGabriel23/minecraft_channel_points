# core/commands.py
import asyncio
import json
import uuid
from typing import Dict, Any
from fastapi import HTTPException
from bedrock.response import CommandResponse
from core.state import active_connections, command_requests

# Clase para simular el servidor de BedrockPy
class FakeServer:
    async def run(self, command: str, *, wait: bool = True) -> CommandResponse | None:
        return await send_minecraft_command(command)

async def send_minecraft_command(command: str, wait: bool = True) -> CommandResponse | None:
    if not active_connections:
        raise HTTPException(status_code=503, detail="No hay jugadores de Minecraft conectados.")

    command_id = str(uuid.uuid4())
    command_payload = {
        "header": {
            "version": 1,
            "requestId": command_id,
            "messagePurpose": "commandRequest",
            "messageType": "commandRequest"
        },
        "body": {
            "commandLine": command,
            "version": 1,
        },
    }
    
    if wait:
        future = asyncio.get_event_loop().create_future()
        command_requests[command_id] = future
    
    
    connection = active_connections[0]
    await connection.send_text(json.dumps(command_payload))
    
    if wait:
        try:
            print(f"Comando enviado: {command}")
            result = await asyncio.wait_for(future, timeout=5.0)
            print(f"Resultado: {result}")
            return result
        except asyncio.TimeoutError:
            if command_id in command_requests:
                del command_requests[command_id]
            raise HTTPException(status_code=504, detail="El servidor de Minecraft no respondió a tiempo.")

    return None