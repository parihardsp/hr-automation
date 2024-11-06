# dialogs/main_dialog.py
import aiohttp
from botbuilder.core import MessageFactory
from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
)
from botbuilder.dialogs.prompts import OAuthPrompt, OAuthPromptSettings
from botbuilder.schema import HeroCard, CardAction, Attachment, ActionTypes


class MainDialog(ComponentDialog):
    def __init__(self, connection_name: str):
        super().__init__(MainDialog.__name__)

        self.connection_name = connection_name

        # Add OAuth prompt
        self.add_dialog(
            OAuthPrompt(
                "OAuthPrompt",
                OAuthPromptSettings(
                    connection_name=connection_name,
                    text="Please sign in to access CV Bot features",
                    title="Sign In",
                    timeout=300000,
                ),
            )
        )

        # Add waterfall dialog
        self.add_dialog(
            WaterfallDialog(
                "WFDialog", [
                    self.auth_step,
                    self.process_token_step,
                    self.show_menu_step,
                ]
            )
        )

        self.initial_dialog_id = "WFDialog"

    async def auth_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        return await step_context.begin_dialog("OAuthPrompt")

    async def process_token_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if step_context.result:
            token = step_context.result.token
            # Get user info using Microsoft Graph API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                ) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        user_name = user_data.get("displayName", "User")

                        # Store the user's name in the bot
                        step_context.context.activity.get_conversation_reference().user.name = user_name
                        await step_context.context.send_activity(f"Hey {user_name}!"
                                                                 f"Welcome to CV Bot, Please Select any of the options to get started")
                        return await step_context.next(user_data)

        await step_context.context.send_activity("Login failed. Please try again.")
        return await step_context.end_dialog()

    async def show_menu_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        card = HeroCard(
            title="CV Bot Menu",
            subtitle="Please select an option:",
            buttons=[
                CardAction(
                    type=ActionTypes.im_back,
                    title="Create a JD",
                    value="create a jd"
                ),
                CardAction(
                    type=ActionTypes.im_back,
                    title="Fetch Resumes",
                    value="fetch resumes"
                )
            ]
        )

        message = MessageFactory.attachment(
            Attachment(
                content_type="application/vnd.microsoft.card.hero",
                content=card
            )
        )

        await step_context.context.send_activity(message)
        return await step_context.end_dialog()

