# bot/cv_bot.py
from botbuilder.core import ActivityHandler, TurnContext, ConversationState, UserState, MessageFactory
from botbuilder.dialogs import Dialog
from hr_bot.dialogs.dialog_helper import DialogHelper
from hr_bot.bot.bot_modules.create_jd import JobDescriptionHandler
from botbuilder.schema import HeroCard, CardAction, ActionTypes, Attachment


class CVBot(ActivityHandler):
    def __init__(
            self,
            conversation_state: ConversationState,
            user_state: UserState,
            dialog: Dialog,
    ):
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.dialog = dialog
        self.job_description_handler = JobDescriptionHandler()  # Initialize the handler
        self.user_display_name = None  # To store user's name after authentication

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    async def display_main_menu(self, turn_context: TurnContext):
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

        await turn_context.send_activity(
            MessageFactory.attachment(
                Attachment(
                    content_type="application/vnd.microsoft.card.hero",
                    content=card
                )
            )
        )

    async def on_message_activity(self, turn_context: TurnContext):
        user_message = turn_context.activity.text.lower() if turn_context.activity.text else ""

        if user_message == "create a jd":
            await turn_context.send_activity("Alright! I'll create a detailed and tailored job description. "
                                             "It won't take long, and I'll ask you some questions to better understand what you're looking for.")
            await self.job_description_handler.start_job_description(turn_context)

        elif self.job_description_handler.is_active():
            await self.job_description_handler.handle_message(turn_context)

        elif user_message == "fetch resumes":
            await turn_context.send_activity("Fetching resumes using CV-Scorer...")

        else:
            # For other messages, run the dialog (handles authentication)
            await DialogHelper.run_dialog(
                self.dialog,
                turn_context,
                self.conversation_state.create_property("DialogState"),
            )

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Welcome to CV Bot! Type anything to get started.")