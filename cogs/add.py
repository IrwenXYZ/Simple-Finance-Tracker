import pandas as pd
from telebot import types


class AddCommandCog:
    def __init__(self, bot, allowed_user_id, categories_cog):
        self.bot = bot
        self.ALLOWED_USER_ID = allowed_user_id
        self.categories_cog = categories_cog  # Store reference to categories cog
        self.user_data = {}

        # Register command handler
        @bot.message_handler(commands=['add'])
        def add_command_handler(message):
            self.add_command(message)

    def is_authorized(self, message):
        return message.from_user.id == self.ALLOWED_USER_ID

    def add_command(self, message):
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        # Initialize user data
        self.user_data[message.from_user.id] = {"step": "name"}

        # Ask for the name
        msg = self.bot.reply_to(message, "Please enter the name:")
        self.bot.register_next_step_handler(msg, self.process_name_step)

    # step 1: get name of transaction
    def process_name_step(self, message):
        if not self.is_authorized(message):
            return

        user_id = message.from_user.id
        self.user_data[user_id]["name"] = message.text
        self.user_data[user_id]["step"] = "category"

        # Get categories from categories cog
        categories = self.categories_cog.get_categories()

        if not categories:
            self.bot.reply_to(message, "No categories available. Please use /addcategory to add some first.")
            return

        # Create inline keyboard with category buttons
        markup = types.InlineKeyboardMarkup(row_width=2)
        category_buttons = []

        for category in categories:
            category_buttons.append(types.InlineKeyboardButton(
                text=category,
                callback_data=f"category_{category}"
            ))

        markup.add(*category_buttons)

        # Ask for the category with inline buttons
        self.bot.send_message(
            message.chat.id,
            "Please select a category:",
            reply_markup=markup
        )

    def setup_callback_handlers(self):
        # This needs to be called after cog initialization
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
        def process_category_callback(call):
            self.process_category_callback_impl(call)

    # step 2 & 3: get category & amount
    def process_category_callback_impl(self, call):
        user_id = call.from_user.id

        if user_id != self.ALLOWED_USER_ID:
            return

        # Extract category from callback data
        selected_category = call.data.split('_')[1]
        self.user_data[user_id]["category"] = selected_category
        self.user_data[user_id]["step"] = "amount"

        # Edit the message to show selection
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Selected category: {selected_category}"
        )

        # Ask for the amount
        msg = self.bot.send_message(call.message.chat.id, "Please enter the amount:")
        self.bot.register_next_step_handler(msg, self.process_amount_step)

    def process_amount_step(self, message):
        if not self.is_authorized(message):
            return

        user_id = message.from_user.id

        # Validate amount is a number
        try:
            amount = float(message.text)
            self.user_data[user_id]["amount"] = amount
        except ValueError:
            msg = self.bot.reply_to(message, "Please enter a valid number for the amount:")
            self.bot.register_next_step_handler(msg, self.process_amount_step)
            return

        # Store summary details before saving and clearing user_data
        name = self.user_data[user_id].get("name", "Unknown")
        category = self.user_data[user_id].get("category", "Unknown")
        amount_val = self.user_data[user_id].get("amount", 0)

        # Save data to Excel
        self.save_to_excel(user_id)

        # Show summary to user
        summary = (
            f"Entry saved successfully!\n\n"
            f"Name: {name}\n"
            f"Category: {category}\n"
            f"Amount: {amount_val}"
        )
        self.bot.reply_to(message, summary)

    def save_to_excel(self, user_id):
        file_path = 'expenses.xlsx'

        # Create a new row with the user's data
        new_data = {
            'Name': [self.user_data[user_id]["name"]],
            'Category': [self.user_data[user_id]["category"]],
            'Amount': [self.user_data[user_id]["amount"]]
        }
        new_df = pd.DataFrame(new_data)

        # Check if file exists
        try:
            # If file exists, append to it
            existing_df = pd.read_excel(file_path)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        except FileNotFoundError:
            # If file doesn't exist, create a new one
            updated_df = new_df

        # Save to Excel
        updated_df.to_excel(file_path, index=False)

        # Clear user data
        self.user_data.pop(user_id)
