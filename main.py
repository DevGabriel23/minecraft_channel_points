import asyncio
import json
import random
import time
import uuid
from typing import List, Dict, Any, Callable, Awaitable

import convert_case
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from starlette.middleware.cors import CORSMiddleware
from bedrock.context import get_game_context, GameContext, PlayerTransformContext
from bedrock.events import GameEvent
from bedrock.response import CommandResponse
from models import MobRequest, TeleportRequest, ItemRequest
from config.const import mob_type_name, articles_by_mob_type, colors_by_code

# --- Variables Globales ---
player_data: Dict[str, Dict] = {}
game_event_handlers: List[GameEvent] = []
active_connections: List[WebSocket] = []
command_requests: Dict[str, asyncio.Future] = {} 

# =========================================================================
# === CLASE PARA SIMULAR EL SERVIDOR DE BEDROCKPY =========================
# =========================================================================
class FakeServer:
    """
    Clase para simular el objeto 'Server' que las clases Context de BedrockPy esperan.
    """
    async def run(self, command: str, *, wait: bool = True) -> CommandResponse | None:
        return await send_minecraft_command(command)

# Creamos una instancia de nuestro servidor simulado
fake_bedrock_server = FakeServer()

# Decorador para registrar eventos del juego de manera similar a BedrockPy
def game_event(fn: Callable[[GameContext], Awaitable[Any]]) -> GameEvent:
    event_name = fn.__name__.replace('_', ' ')
    event_name = convert_case.pascal_case(event_name)
    event = GameEvent(event_name, fn)
    game_event_handlers.append(event)
    return event

# =========================================================================
# === APLICACIÓN FASTAPI ==================================================
# =========================================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# === LÓGICA DE WEBSOCKET Y COMANDOS ======================================
# =========================================================================

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

@app.websocket("/ws")
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
            return await asyncio.wait_for(future, timeout=5.0)
        except asyncio.TimeoutError:
            if command_id in command_requests:
                del command_requests[command_id]
            raise HTTPException(status_code=504, detail="El servidor de Minecraft no respondió a tiempo.")

    return None

# =========================================================================
# === MANEJADORES DE EVENTOS DE JUEGO (GAME EVENT HANDLERS) ===============
# =========================================================================

@game_event
async def player_transform(ctx: PlayerTransformContext):
    """Se dispara cuando la posición o rotación del jugador cambia."""
    player_name = ctx.player
    player_pos = ctx.player_position
    
    x = player_pos[0].coord
    y = player_pos[1].coord
    z = player_pos[2].coord
    
    player_data[player_name] = {
        "position": {"x": x, "y": y, "z": z},
    }

    # print(f"Posición de {player_name} actualizada: x={x}, y={y}, z={z}")


@game_event
async def player_join(ctx: GameContext):
    """Se dispara cuando un jugador se une."""
    # En este caso, el evento player_join no tiene una clase de contexto específica,
    # así que usamos la clase base GameContext para acceder a los datos.
    player_name = ctx.data.get("player", {}).get("name")
    if player_name:
        player_data[player_name] = {"position": None}
        print(f"El jugador {player_name} se ha unido al mundo.")


# =========================================================================
# === RUTAS DE LA API (HTTP) ==============================================
# =========================================================================

@app.get("/player_data/{player_name}")
async def get_player_data(player_name: str):
    if player_name in player_data:
        return player_data[player_name]
    else:
        raise HTTPException(status_code=404, detail=f"No se encontró información para el jugador {player_name}.")

@app.post("/spawn_mob_at_player")
async def spawn_mob_at_player(request: MobRequest, player_name: str | None = None, username: str | None = None):
    if not player_data:
        raise HTTPException(status_code=404, detail="No hay jugadores conectados.")

    selected_player_name = None
    
    if player_name == "random" or player_name is None:
        selected_player_name = random.choice(list(player_data.keys()))
        print(f"Spawning mob at random player: {selected_player_name}")
    elif player_name in player_data:
        selected_player_name = player_name
        print(f"Spawning mob at specified player: {selected_player_name}")
    else:
        raise HTTPException(status_code=404, detail=f"No se encontró información de ubicación para el jugador {player_name}.")

    player_pos_data = player_data[selected_player_name]["position"]
    
    if not player_pos_data:
        raise HTTPException(status_code=404, detail=f"No se encontró información de ubicación para el jugador {selected_player_name}.")
    
    mob_name = ' '
    title_command = f"title {selected_player_name} actionbar \"§aHas spawneado {articles_by_mob_type[request.mob_type]} {mob_type_name[request.mob_type]}!\""
    if username is not None:
        color = random.choice(list(colors_by_code.keys()))
        while color in ['§0', '§a']:
            color = random.choice(list(colors_by_code.keys()))
        mob_name = f' "{color}{username}" '
        title_command = f"title {selected_player_name} actionbar \"§aHa spawneado {color}{username} §a({mob_type_name[request.mob_type]})!\""
    
    command = f"summon {request.mob_type}{mob_name}{player_pos_data['x']} {player_pos_data['y']} {player_pos_data['z']}"
    
    await send_minecraft_command(command)
    await send_minecraft_command(title_command)
    
    return {
        "message": f"Mob {request.mob_type} spawnado en {selected_player_name}.", 
        "mob_type": request.mob_type, "player": selected_player_name,
        "article": articles_by_mob_type[request.mob_type],
        "mob_name": mob_type_name[request.mob_type],
        "username": username if username else "N/A"
    }

DANGEROUS_BLOCKS = ["lava", "flowing_lava", "fire", "air"]
GRAVITY_BLOCKS = ["sand", "gravel"]

# Función para verificar si una ubicación es segura
async def is_safe_location(x: int, y: int, z: int) -> tuple[bool, str]:
    # 1. Comprueba si los bloques de los pies y la cabeza están libres
    feet_air_response = await send_minecraft_command(f"testforblock {x} {y} {z} air")
    head_air_response = await send_minecraft_command(f"testforblock {x} {y + 1} {z} air")
    
    if feet_air_response.status != 0 or head_air_response.status != 0:
        print(f"{feet_air_response}\n{head_air_response}")
        return False, "no_space"

    # 2. Comprueba si el bloque de abajo es sólido y no peligroso
    block_below_is_air_response = await send_minecraft_command(f"testforblock {x} {y - 1} {z} air")
    if block_below_is_air_response.status == 0:
        return False, "no_floor"
    
    for block in DANGEROUS_BLOCKS:
        dangerous_block_response = await send_minecraft_command(f"testforblock {x} {y - 1} {z} {block}")
        if dangerous_block_response.status == 0:
            return False, "dangerous_block"
        else:
            print(f"{dangerous_block_response}")

    return True, "safe"

@app.post("/teleport_player")
async def teleport_player(request: TeleportRequest, player_name: str | None = None, username: str | None = None):
    if not player_data:
        raise HTTPException(status_code=404, detail="No hay jugadores conectados.")

    selected_player_name = None
    
    if player_name == "random" or player_name is None:
        selected_player_name = random.choice(list(player_data.keys()))
        print(f"Teleporting at random player: {selected_player_name}")
    elif player_name in player_data:
        selected_player_name = player_name
        print(f"Teleporting at specified player: {selected_player_name}")
    else:
        raise HTTPException(status_code=404, detail=f"No se encontró información de ubicación para el jugador {player_name}.")

    player_pos_data: dict | None = player_data[selected_player_name]["position"]
    
    if not player_pos_data:
        raise HTTPException(status_code=404, detail=f"No se encontró información de ubicación para el jugador {selected_player_name}.")
    
    random_x = random.randint(-3000, 3000)
    random_z = random.randint(-3000, 3000)
    
    destination_x = request.x if request.x is not None else player_pos_data['x'] + random_x
    destination_y = request.y if request.y is not None else player_pos_data['y']
    destination_z = request.z if request.z is not None else player_pos_data['z'] + random_z
    # Creamos una tickingarea temporal para cargar la zona de destino
    tickingarea_add_teleport_area = f"tickingarea add {int(destination_x) - 1} -64 {int(destination_z) - 1} {int(destination_x) + 1} 320 {int(destination_z) + 1} teleport_area"
    tickingarea_add_teleport_area_response = await send_minecraft_command(tickingarea_add_teleport_area)
    print(tickingarea_add_teleport_area)
    print(tickingarea_add_teleport_area_response)
    await send_minecraft_command(f"tp {selected_player_name} {int(destination_x)} 320 {int(destination_z)}")
    await asyncio.sleep(1)
    # Aseguramos que la coordenada Y sea segura (no dentro de un bloque sólido)
    start_time = time.time()
    
    safe_destination_y = None
    low = 63
    high = 320 # Rango de altura en Minecraft Bedrock
    last_high = 320
    i = 1
    print(f"{int(destination_x)}, {int(destination_y)}, {int(destination_z)}")
    while low <= high:
        mid = (low + high) // 2
        is_safe, reason = await is_safe_location(int(destination_x), mid, int(destination_z))
        print(f"Test: {i} - Buscando en Y={mid}, rango: {low} a {high} - {reason}")
        i = i + 1
        if is_safe:
            # Si es seguro, guarda esta posición y busca una más alta
            safe_destination_y = mid
            low = mid + 1
        elif reason == "no_floor":
            # Si no hay piso (es aire), busca más abajo y guarda la última altura alta conocida (ya que desde el punto más alto original hasta esta, sabemos que es aire)
            last_high = high
            high = mid - 1
        elif reason == "no_space":
            # Si no hay espacio (bloque sólido en los pies o cabeza), busca más arriba
            low = mid + 1
            high = last_high
        else: # "no_space", "dangerous_block", "gravity_block"
            # Si está bloqueado o es peligroso, repite la validacion en la misma altura pero cambiando X y Z ligeramente
            destination_x = int(destination_x) + random.randint(-5, 5)
            destination_z = int(destination_z) + random.randint(-5, 5)

    if safe_destination_y is None:
        await send_minecraft_command("tickingarea remove_all")
        raise HTTPException(status_code=400, detail="No se pudo encontrar una ubicación segura para teletransportar al jugador.")
    else:
        await send_minecraft_command("tickingarea remove_all")
        print(f"Ubicación segura encontrada en Y={safe_destination_y}")
        destination_y = safe_destination_y
        
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"El código tardó {execution_time} segundos en ejecutarse.")
            
    command = f"tp {selected_player_name} {int(destination_x)} {int(destination_y)} {int(destination_z)}"
    
    twitch_username = ''
    if username is not None:
        color = random.choice(list(colors_by_code.keys()))
        twitch_username += f' por {color}{username} §a'    
    
    distance_in_meters = ((int(destination_x) - int(player_pos_data['x'])) ** 2 +
                (int(destination_y) - int(player_pos_data['y'])) ** 2 +
                (int(destination_z) - int(player_pos_data['z'])) ** 2) ** 0.5

    distance_in_km = int((distance_in_meters / 1000.0) * 100) / 100
    
    alert_command = f"title {selected_player_name} actionbar \"§aHas sido teletransportado{twitch_username}a {int(destination_x)}, {int(destination_y)}, {int(destination_z)}\""
    chat_command = f"msg @s §aHas sido teletransportado {distance_in_km}km{twitch_username} ({int(player_pos_data['x'])}, {int(player_pos_data['y'])}, {int(player_pos_data['z'])})"
    
    print(command)
    print(alert_command)
    print(chat_command)
    
    await send_minecraft_command(command, wait=False)
    await send_minecraft_command(alert_command, wait=False)
    await send_minecraft_command(chat_command, wait=False)
    
    return {
        "message": f"Jugador {selected_player_name} teletransportado a {int(destination_x)}, {int(destination_y)}, {int(destination_z)}.",
        "player": selected_player_name,
        "coordinates": {
            "x": int(destination_x),
            "y": int(destination_y),
            "z": int(destination_z)
        }
    } 

@app.post("/give_item")
async def give_item(request: ItemRequest):
    command = f"give {request.player_name} {request.item_id} {request.amount}"
    return await send_minecraft_command(command)

@app.post("/take_item")
async def take_item(request: ItemRequest):
    command = f"clear {request.player_name} {request.item_id} {request.amount}"
    return await send_minecraft_command(command)