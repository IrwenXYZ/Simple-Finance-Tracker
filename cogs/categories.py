import json
import os
import pandas as pd
from telebot import types


class CategoriesCog:
    def __init__(self, bot, allowed_user_id):
        self.bot = bot
        self.ALLOWED_USER_ID = allowed_user_id
        self.categories_file = "categories.json"
        self.categories = self.load_categories()

        # Register command handlers
        @bot.message_handler(commands=['categories'])
        def categories_command_handler(message):
            self.list_categories_command(message)

        @bot.message_handler(commands=['addcategory'])
        def add_category_handler(message):
            self.add_category_command(message)

        @bot.message_handler(commands=['removecategory'])
        def remove_category_handler(message):
            self.remove_category_command(message)

        @bot.message_handler(commands=['editcategory'])
        def edit_category_handler(message):
            self.edit_category_command(message)

    def is_authorized(self, message):
        return message.from_user.id == self.ALLOWED_USER_ID

    def load_categories(self):
        """Load categories from JSON file or return defaults if file doesn't exist"""
        default_categories = ["Food", "Transportation", "Entertainment", "Utilities", "Shopping", "Health", "Car", "Other"]

        if os.path.exists(self.categories_file):
            try:
                with open(self.categories_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return default_categories
        else:
            # Save defaults to file
            with open(self.categories_file, 'w') as f:
                json.dump(default_categories, f)
            return default_categories

    def save_categories(self):
        """Save categories to JSON file"""
        with open(self.categories_file, 'w') as f:
            json.dump(self.categories, f)

    def get_categories(self):
        """Return the current list of categories"""
        return self.categories

    def list_categories_command(self, message):
        """Command to list all available categories"""
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        if not self.categories:
            self.bot.reply_to(message, "No categories defined. Use /addcategory to add some.")
            return

        categories_text = "Available categories:\n\n" + "\n".join([f"• {category}" for category in self.categories])
        self.bot.reply_to(message, categories_text)

    def add_category_command(self, message):
        """Command to add a new category"""
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        msg = self.bot.reply_to(message, "What category would you like to add?")
        self.bot.register_next_step_handler(msg, self.process_add_category)

    def process_add_category(self, message):
        """Process the new category name"""
        if not self.is_authorized(message):
            return

        new_category = message.text.strip()

        if not new_category:
            self.bot.reply_to(message, "Category name cannot be empty.")
            return

        if new_category in self.categories:
            self.bot.reply_to(message, f"Category '{new_category}' already exists.")
            return

        self.categories.append(new_category)
        self.save_categories()
        self.bot.reply_to(message, f"Category '{new_category}' added successfully!")

    def remove_category_command(self, message):
        """Command to remove a category"""
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        if not self.categories:
            self.bot.reply_to(message, "No categories to remove.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = []

        for category in self.categories:
            buttons.append(types.InlineKeyboardButton(
                text=category,
                callback_data=f"remove_cat_{category}"
            ))

        markup.add(*buttons)
        self.bot.send_message(
            message.chat.id,
            "Select a category to remove:",
            reply_markup=markup
        )

    def process_remove_category_callback_impl(self, call):
        """Process the category removal selection"""
        user_id = call.from_user.id

        if user_id != self.ALLOWED_USER_ID:
            return

        # Extract category from callback data
        category_to_remove = call.data.replace('remove_cat_', '', 1)

        if category_to_remove in self.categories:
            self.categories.remove(category_to_remove)
            self.save_categories()

            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Category '{category_to_remove}' has been removed."
            )
        else:
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Category '{category_to_remove}' not found or already removed."
            )

    def edit_category_command(self, message):
        """Command to edit a category name"""
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        if not self.categories:
            self.bot.reply_to(message, "No categories to edit.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = []

        for category in self.categories:
            buttons.append(types.InlineKeyboardButton(
                text=category,
                callback_data=f"edit_cat_{category}"
            ))

        markup.add(*buttons)
        self.bot.send_message(
            message.chat.id,
            "Select a category to edit:",
            reply_markup=markup
        )

    def process_edit_category_callback_impl(self, call):
        """Process the category edit selection"""
        user_id = call.from_user.id

        if user_id != self.ALLOWED_USER_ID:
            return

        # Extract category from callback data
        category_to_edit = call.data.replace('edit_cat_', '', 1)

        if category_to_edit in self.categories:
            # Store the category being edited
            self.edit_category_session[user_id] = category_to_edit

            # Edit message to show selected category
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"You are editing category: '{category_to_edit}'\nPlease enter the new name:"
            )

            # Register next step handler to get new category name
            self.bot.register_next_step_handler(call.message, self.process_new_category_name)
        else:
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Category '{category_to_edit}' not found."
            )

    def process_new_category_name(self, message):
        """Process the new category name"""
        if not self.is_authorized(message):
            return

        user_id = message.from_user.id

        # Get the old category name from session
        if user_id not in self.edit_category_session:
            self.bot.reply_to(message, "Session expired. Please try again.")
            return

        old_category = self.edit_category_session[user_id]
        new_category = message.text.strip()

        if not new_category:
            self.bot.reply_to(message, "Category name cannot be empty.")
            return

        if new_category in self.categories and new_category != old_category:
            self.bot.reply_to(message, f"Category '{new_category}' already exists.")
            return

        # Update the category in the list
        index = self.categories.index(old_category)
        self.categories[index] = new_category
        self.save_categories()

        # Update Excel sheet
        updated_count = self.update_category_in_excel(old_category, new_category)

        # Clean up session
        del self.edit_category_session[user_id]

        if updated_count > 0:
            self.bot.reply_to(message,
                              f"Category renamed from '{old_category}' to '{new_category}' successfully!\n"
                              f"Updated {updated_count} existing entries in the expense sheet.")
        else:
            self.bot.reply_to(message,
                              f"Category renamed from '{old_category}' to '{new_category}' successfully!\n"
                              f"No existing entries needed updating.")

    def update_category_in_excel(self, old_category, new_category):
        """Update all instances of old_category to new_category in the Excel file"""
        excel_file = 'expenses.xlsx'
        updated_count = 0

        try:
            # Check if the Excel file exists
            if not os.path.exists(excel_file):
                # If the file doesn't exist, there's nothing to update
                return updated_count

            # Read the Excel file
            df = pd.read_excel(excel_file)

            # Check if the Category column exists
            if 'Category' not in df.columns:
                return updated_count

            # Find all rows with the old category and update them
            mask = df['Category'] == old_category
            updated_count = mask.sum()

            if updated_count > 0:
                df.loc[mask, 'Category'] = new_category

                # Save the updated dataframe
                df.to_excel(excel_file, index=False)

            return updated_count

        except Exception as e:
            print(f"Error updating Excel file: {e}")
            return updated_count

    def setup_callback_handlers(self):
        """Setup callback handlers for this cog"""
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('remove_cat_'))
        def process_remove_category_callback(call):
            self.process_remove_category_callback_impl(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('edit_cat_'))
        def process_edit_category_callback(call):
            self.process_edit_category_callback_impl(call)
