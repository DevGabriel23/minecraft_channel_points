# Minecraft Channel Points API

Este proyecto es una API basada en FastAPI que permite interactuar con un servidor de Minecraft Bedrock a través de comandos y eventos, integrando funcionalidades como teletransportar jugadores, dar/quitar ítems y spawnear mobs, todo controlado mediante endpoints HTTP y WebSocket.

## Estructura del Proyecto

- `main.py`: Lógica principal de la API, manejo de eventos, rutas HTTP y WebSocket.
- `models/`: Modelos de datos Pydantic para las solicitudes de la API.
	- `item_request.py`: Modelo para dar/quitar ítems.
	- `mob_request.py`: Modelo para spawnear mobs.
	- `teleport_request.py`: Modelo para teletransportar jugadores.
- `config/const.py`: Diccionarios de configuración para nombres de mobs, artículos y colores.
- `.vscode/`: Configuración para depuración en VSCode.
- `requirements.txt`: Dependencias del proyecto.

## Requisitos

- Python 3.10+
- Minecraft Bedrock Server (con BedrockPy)
- Las dependencias listadas en `requirements.txt`

## Instalación

1. **Clona el repositorio**  
	 ```sh
	 git clone <URL-del-repo>
	 cd <carpeta-del-proyecto>
	 ```

2. **Instala las dependencias**  
	 ```sh
	 pip install -r requirements.txt
	 ```

3. **Configura el entorno**  
	 Si usas variables de entorno, crea un archivo `.env` en la raíz.

## Ejecución

Puedes iniciar la API usando Uvicorn:

```sh
uvicorn main:app --reload
```

O, si usas Visual Studio Code, simplemente ejecuta la configuración de depuración incluida en `.vscode/launch.json`.

## Endpoints principales

- **WebSocket:** `/ws`  
	Para conectar el cliente de Minecraft y recibir eventos.
- **GET `/player_data/{player_name}`**  
	Obtiene la posición actual de un jugador.
- **POST `/spawn_mob_at_player`**  
	Spawnea un mob en la posición de un jugador.
- **POST `/teleport_player`**  
	Teletransporta a un jugador a una ubicación segura.
- **POST `/give_item`**  
	Da ítems a un jugador.
- **POST `/take_item`**  
	Quita ítems a un jugador.

## Notas

- El servidor espera que el cliente de Minecraft esté conectado vía WebSocket.
- Los comandos se envían y reciben usando el protocolo de BedrockPy.

---

Para más detalles revisa los archivos fuente:  
- `main.py`  
- `models/item_request.py`  
- `models/mob_request.py`  
- `models/teleport_request.py`  
- `config/const.py`
