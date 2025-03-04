# app.py
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapter,  # Changed import location
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


APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    try:
        web.run_app(APP, host="localhost", port=CONFIG.PORT)
    except Exception as error:
        raise error
