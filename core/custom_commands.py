# core/custom_commands.py
import asyncio
from utils.timer import send_countdown_timer
from core.commands import send_minecraft_command
from core.state import player_data

async def handle_timer_command(params: list[str], sender: str):
    """Maneja el comando '!timer' y sus subcomandos para un jugador específico."""
    
    if sender not in player_data:
        player_data[sender] = {"timer": {"is_running": False, "task": None, "remaining_time": 0}}
    if "timer" not in player_data[sender]:
        player_data[sender]["timer"] = {"is_running": False, "task": None, "remaining_time": 0}

    # Ahora accedemos directamente al diccionario, no a variables locales
    timer_data = player_data[sender]["timer"]

    if len(params) == 0:
        await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§cUso incorrecto: !timer <iniciar|detener|estado> <duracion>"}}]}}', wait=False)
        return
    
    subcommand = params[0].lower()
    
    match subcommand:
        case "start":
            if timer_data["is_running"]:
                await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§eTu cronómetro ya está en marcha."}}]}}')
                return
            
            try:
                if len(params) > 2:
                    mode = params[2].lower()
                else:
                    mode = "once"

                duration = int(params[1])
                if duration <= 0:
                    await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§cLa duración debe ser un número positivo."}}]}}', wait=False)
                    return
                
                if mode not in ['loop', 'once']:
                    await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§cModo no válido. Usa \"loop\" o \"once\"."}}]}}', wait=False)
                    return

                timer_data["is_running"] = True
                timer_data["remaining_time"] = duration
                timer_data["initial_duration"] = duration # Guarda la duración inicial para el modo loop
                timer_data["mode"] = mode # Guarda el modo en el diccionario
                
                task = asyncio.create_task(send_countdown_timer(duration, player_data, sender))
                timer_data["task"] = task

                await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§aEl cronómetro ha iniciado por {duration} segundos en modo \'{mode}\'."}}]}}', wait=False)
            except (IndexError, ValueError):
                await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§cUso incorrecto: !timer start <duration_in_seconds>\"}}]}}', wait=False)
        case "stop":
            if not timer_data["is_running"]:
                await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§eNo tienes un cronómetro en ejecución."}}]}}', wait=False)
                return

            task = timer_data["task"]

            if task and not task.done():
                task.cancel()
                await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§aTu cronómetro ha sido detenido."}}]}}', wait=False)
            else:
                await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§eError: El temporizador no pudo ser detenido. Inténtalo de nuevo."}}]}}', wait=False)
            
        case "status":
            if timer_data["is_running"]:
                await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§eEl cronómetro está en marcha. Tiempo restante: {timer_data["remaining_time"]}s"}}]}}', wait=False)
            else:
                await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§aEl cronómetro está detenido."}}]}}', wait=False)
        case _:
            await send_minecraft_command(f'tellraw "{sender}" {{"rawtext":[{{"text":"§cSubcomando desconocido: {subcommand}."}}]}}', wait=False)

async def parse_and_execute_command(message: str, sender: str):
    """
    Analiza un mensaje y ejecuta el comando personalizado.
    Ej: !cronometro iniciar 60
    """
    parts = message.strip().lower().split()
    command = parts[0]
    params = parts[1:]

    match command:
        case "!timer":
            await handle_timer_command(params, sender)
        # Puedes añadir otros comandos aquí
        # case "!spawn":
        #     await handle_spawn_command(params, sender)
        case _:
            await send_minecraft_command(f"tellraw @a {{\"rawtext\":[{{\"text\":\"§cComando desconocido.\"}}]}}", wait=False)