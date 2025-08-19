# utils/timer.py
import asyncio
import random
from typing import Dict, Any

from fastapi import HTTPException
from core.commands import send_minecraft_command
from config.const import random_events
from api.routes import roulette_effect, spawn_mob_at_player, teleport_player
from core.commands import send_minecraft_command

async def send_countdown_timer(duration: int, player_data: Dict[str, Any], player_name: str):
    """
    Envía una cuenta regresiva a la barra de acción de un jugador específico.

    Args:
        duration (int): La duración del temporizador en segundos.
        player_data (Dict[str, Any]): El diccionario global con el estado de los jugadores.
        player_name (str): El nombre del jugador para el que se inicia el temporizador.
    """
    
    # Asegúrate de que el jugador existe en los datos
    if player_name not in player_data:
        raise HTTPException(status_code=404, detail=f"No se encontró al jugador {player_name}.")

    timer_data = player_data[player_name]['timer']
    
    try:
        while True:
            remaining_time = timer_data.get("remaining_time", 0)
            while timer_data.get('is_running', False) and remaining_time >= 0:
                minutes = remaining_time // 60
                seconds = remaining_time % 60
                
                player_data[player_name]['timer']['remaining_time'] = remaining_time
                
                # Formato del texto para la barra de acción
                timer_text = f"§6{minutes:02d}m {seconds:02d}s §6"
                
                await send_minecraft_command(f'titleraw "{player_name}" actionbar {{"rawtext":[{{"text":"{timer_text}"}}]}}', wait=False)

                await asyncio.sleep(1)
                remaining_time -= 1
            
            if timer_data["is_running"]:
                # Ejecuta un evento aleatorio
                await run_random_event(player_data, player_name)
            
            if timer_data["mode"] == "loop" and timer_data["is_running"]:
                # Reinicia el temporizador si el modo es "loop" y no ha sido detenido
                timer_data["remaining_time"] = timer_data.get("initial_duration", 0)
                await send_minecraft_command(f'tellraw "{player_name}" {{"rawtext":[{{"text":"§eEl cronómetro se está reiniciando..."}}]}}', wait=False)
                # Vuelve al inicio del bucle exterior
                continue
            else:
                # Sale del bucle si el modo es "once" o el temporizador fue detenido
                break
            
    except asyncio.CancelledError:
        # Esta excepción se dispara cuando se llama a `task.cancel()`
        print(f"Temporizador para {player_name} cancelado.")
    except HTTPException as e:
        # Manejamos errores si la conexión se pierde
        print(f"HTTPException en el temporizador: {e.detail}")
    finally:
        if player_name in player_data and 'timer' in player_data[player_name]:
            timer_data['is_running'] = False
            timer_data['task'] = None

    # Limpia la barra de acción una última vez si el bucle terminó
    await send_minecraft_command(f'title {player_name} actionbar ""',  wait=False)

async def run_random_event(player_data: Dict[str, Any], player_name: str):
    """
    Selecciona un evento aleatorio de la lista y lo ejecuta.
    """
    if not player_data:
        await send_minecraft_command(f'tellraw "{player_name}" {{"rawtext":[{{"text":"§cNo hay jugadores conectados. No se puede ejecutar el evento."}}]}}', wait=False)
        return

    # Elige un evento al azar de la lista
    event_to_run = random.choice(random_events)
    
    # Prepara los argumentos y el nombre de la función a llamar
    command_name = event_to_run["command"]
    args: Dict = event_to_run["args"]
    
    # Actualiza el nombre del jugador si es necesario
    if args.get("player_name") == "random":
        args["player_name"] = random.choice(list(player_data.keys()))
    else:
        args["player_name"] = player_name

    await send_minecraft_command(f'tellraw "{player_name}" {{"rawtext":[{{"text":"§e¡El cronómetro ha terminado! \n §cSOBREVIVE A {event_to_run["name"]}."}}]}}', wait=False)

    # Ejecuta la función del evento
    try:
        # Usa un diccionario para llamar a la función correcta
        event_handlers = {
            "spawn_mob_at_player": spawn_mob_at_player,
            "teleport_player": teleport_player,
            "roulette_effect": roulette_effect,
        }
        
        handler = event_handlers.get(command_name)
        if handler:
            # Los argumentos deben ser un objeto Request
            from models import MobRequest, TeleportRequest # Importa tus modelos de datos
            
            # Convierte los argumentos a los modelos de FastAPI si es necesario
            if command_name == "spawn_mob_at_player":
                mob_dict: Dict = args.get("mob_dict", {})
                mob_type = random.choice(list(mob_dict.keys())) if mob_dict else "zombie"
                
                request_obj = MobRequest(mob_type=mob_type)
            elif command_name == "teleport_player":
                request_obj = TeleportRequest(**args)
            else:
                request_obj = None # roulette_effect no necesita un Request body
            
            # Llama a la función del manejador con los argumentos correctos
            if request_obj is None:
                await handler(player_name=args["player_name"], username=args.get("username", "Cronometro"))
            else:
                await handler(request_obj, player_name=args["player_name"], username=args.get("username", "Cronometro"))
        else:
            await send_minecraft_command(f'tellraw "{player_name}" {{"rawtext":[{{"text":"§cError: No se encontró el manejador para {command_name}."}}]}}', wait=False)
    except Exception as e:
        await send_minecraft_command(f'tellraw "{player_name}" {{"rawtext":[{{"text":"§cError al ejecutar el evento: {e}"}}]}}', wait=False)