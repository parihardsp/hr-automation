# # app.py
# from aiohttp import web
# from aiohttp.web import Request, Response, json_response
# from botbuilder.core import (
#     BotFrameworkAdapter,  # Changed import location
#     BotFrameworkAdapterSettings,
#     ConversationState,
#     MemoryStorage,
#     UserState,
# )
# from botbuilder.core.integration import aiohttp_error_middleware
# from botbuilder.schema import Activity
# from botframework.connector.auth import AuthenticationConfiguration

# import config
# from config import DefaultConfig
# from bot.cv_bot import CVBot
# from dialogs.main_dialog import MainDialog

# CONFIG = DefaultConfig()
# SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
# ADAPTER = BotFrameworkAdapter(SETTINGS)

# # Create MemoryStorage, UserState and ConversationState
# MEMORY = MemoryStorage()
# USER_STATE = UserState(MEMORY)
# CONVERSATION_STATE = ConversationState(MEMORY)

# # Create dialogs and bot
# DIALOG = MainDialog(CONFIG.CONNECTION_NAME)
# BOT = CVBot(CONVERSATION_STATE, USER_STATE, DIALOG)


# # Listen for incoming requests on /api/messages
# async def messages(req: Request) -> Response:
#     if "application/json" in req.headers["Content-Type"]:
#         body = await req.json()
#     else:
#         return Response(status=415)

#     activity = Activity().deserialize(body)
#     auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

#     response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
#     if response:
#         return json_response(data=response.body, status=response.status)
#     return Response(status=201)


# APP = web.Application(middlewares=[aiohttp_error_middleware])
# APP.router.add_post("/api/messages", messages)

# if __name__ == "__main__":
#     try:
#         web.run_app(APP, host="localhost", port=CONFIG.PORT)
#     except Exception as error:
#         raise error


# app.py
import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    UserState,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity
from botframework.connector.auth import AuthenticationConfiguration

import config
from config import DefaultConfig
from bot.cv_bot import CVBot
from dialogs.main_dialog import MainDialog

CONFIG = DefaultConfig()
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Create MemoryStorage, UserState and ConversationState
MEMORY = MemoryStorage()
USER_STATE = UserState(MEMORY)
CONVERSATION_STATE = ConversationState(MEMORY)

# Create dialogs and bot
DIALOG = MainDialog(CONFIG.CONNECTION_NAME)
BOT = CVBot(CONVERSATION_STATE, USER_STATE, DIALOG)

# Listen for incoming requests on /api/messages
async def messages(req: Request) -> Response:
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=201)

# Root endpoint
async def root(req: Request) -> Response:
    return Response(text="Your bot is running!")

# Health check endpoint
async def health_check(req: Request) -> Response:
    return Response(text="Healthy")

# Create and configure application
APP = web.Application(middlewares=[aiohttp_error_middleware])

# Add routes
APP.router.add_get("/", root)  # Root endpoint
APP.router.add_get("/health", health_check)  # Health check endpoint
APP.router.add_post("/api/messages", messages)  # Bot messages endpoint

# Modified run block for production
if __name__ == "__main__":
    try:
        PORT = CONFIG.PORT  # This will now use the port from environment variables
        web.run_app(APP, host='0.0.0.0', port=PORT)
    except Exception as error:
        print(f"Error running app: {str(error)}")
        raise error