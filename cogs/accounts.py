import pandas as pd
import os
from telebot import types


class AccountsCog:
    def __init__(self, bot, allowed_user_id):
        self.bot = bot
        self.ALLOWED_USER_ID = allowed_user_id
        self.data_file = "data.xlsx"
        self.sheet_name = "Accounts"
        self.accounts = self.load_accounts()
        self.edit_account_session = {}
        self.onboarding_data = {}

        # Register command handlers
        @bot.message_handler(commands=['accounts'])
        def accounts_command_handler(message):
            self.list_accounts_command(message)

        @bot.message_handler(commands=['addaccount'])
        def add_account_handler(message):
            self.add_account_command(message)

        @bot.message_handler(commands=['removeaccount'])
        def remove_account_handler(message):
            self.remove_account_command(message)

        @bot.message_handler(commands=['editaccount'])
        def edit_account_handler(message):
            self.edit_account_command(message)

    def is_authorized(self, message):
        return message.from_user.id == self.ALLOWED_USER_ID

    def load_accounts(self):
        """Load accounts from Excel file or return defaults if file doesn't exist"""
        default_accounts = ["Cash", "Bank Account", "Credit Card"]

        if os.path.exists(self.data_file):
            try:
                df = pd.read_excel(self.data_file, sheet_name=self.sheet_name)
                return df["Account"].tolist()
            except Exception as e:
                print(f"Error loading accounts from Excel: {e}")
                # Create accounts sheet if it doesn't exist but file does
                self.save_accounts(default_accounts)
                return default_accounts
        else:
            # File doesn't exist, will be created by categories cog or add cog
            return default_accounts

    def save_accounts(self, accounts):
        """Save accounts to Excel file"""
        df = pd.DataFrame({"Account": accounts})

        if os.path.exists(self.data_file):
            try:
                # Try to read all existing sheets to preserve them
                with pd.ExcelWriter(self.data_file, mode='a', if_sheet_exists='replace') as writer:
                    df.to_excel(writer, sheet_name=self.sheet_name, index=False)
            except Exception as e:
                print(f"Error appending to Excel file: {e}")
                # If something goes wrong, just create a new file
                with pd.ExcelWriter(self.data_file) as writer:
                    df.to_excel(writer, sheet_name=self.sheet_name, index=False)
        else:
            # Create new file with only Accounts sheet
            with pd.ExcelWriter(self.data_file) as writer:
                df.to_excel(writer, sheet_name=self.sheet_name, index=False)

    def get_accounts(self):
        """Return the current list of accounts"""
        return self.accounts

    def is_first_time(self):
        """Check if this is the first time the bot is run"""
        return not os.path.exists(self.data_file)

    def start_onboarding(self, message):
        """Start the onboarding process for first-time users"""
        user_id = message.from_user.id
        if not self.is_authorized(message):
            return

        self.onboarding_data[user_id] = {"accounts": []}

        welcome_message = (
            "Welcome to your financial tracker! 📊\n\n"
            "Let's set up your accounts first. These are the sources of your expenses.\n\n"
            "Examples could be: Cash, Bank Account, Credit Card, Savings, etc.\n\n"
            "Let's add your first account. What would you like to call it?"
        )

        msg = self.bot.send_message(message.chat.id, welcome_message)
        self.bot.register_next_step_handler(msg, self.process_onboarding_account)

    def process_onboarding_account(self, message):
        """Process account name during onboarding"""
        if not self.is_authorized(message):
            return

        user_id = message.from_user.id
        account_name = message.text.strip()

        if not account_name:
            msg = self.bot.reply_to(message, "Account name cannot be empty. Please enter a valid name:")
            self.bot.register_next_step_handler(msg, self.process_onboarding_account)
            return

        # Add the account to the onboarding data
        self.onboarding_data[user_id]["accounts"].append(account_name)

        # Ask if they want to add another account
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Yes, add another", callback_data="onboard_more_accounts"),
            types.InlineKeyboardButton("No, I'm done", callback_data="onboard_complete")
        )

        self.bot.send_message(
            message.chat.id,
            f"Account '{account_name}' added! Would you like to add another account?",
            reply_markup=markup
        )

    def finish_onboarding(self, message):
        """Complete the onboarding process"""
        user_id = message.chat.id

        if user_id not in self.onboarding_data:
            return

        accounts = self.onboarding_data[user_id]["accounts"]
        if accounts:
            self.accounts = accounts
            self.save_accounts(accounts)

            # Create default categories sheet
            categories_df = pd.DataFrame({
                "Category": ["Food", "Transportation", "Entertainment", "Utilities", "Shopping", "Health", "Housing", "Other"]
            })

            # Create empty expenses sheet
            expenses_df = pd.DataFrame(columns=["Name", "Account", "Category", "Amount"])

            # Write all sheets to the Excel file
            with pd.ExcelWriter(self.data_file) as writer:
                pd.DataFrame({"Account": accounts}).to_excel(writer, sheet_name="Accounts", index=False)
                categories_df.to_excel(writer, sheet_name="Categories", index=False)
                expenses_df.to_excel(writer, sheet_name="Expenses", index=False)

            completion_message = (
                "✅ Setup complete! Your accounts have been saved.\n\n"
                "You can now start tracking your expenses with the /add command.\n\n"
                "Here are some useful commands:\n"
                "/add - Add a new expense\n"
                "/accounts - List your accounts\n"
                "/categories - List expense categories\n"
                "/help - Show all available commands"
            )

            self.bot.send_message(message.chat.id, completion_message)
        else:
            self.bot.send_message(message.chat.id, "Onboarding canceled. No accounts were added.")

        # Clean up
        del self.onboarding_data[user_id]

    def list_accounts_command(self, message):
        """Command to list all available accounts"""
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        if self.is_first_time():
            self.bot.reply_to(message, "Please complete the initial setup first by using the /start command.")
            return

        if not self.accounts:
            self.bot.reply_to(message, "No accounts defined. Use /addaccount to add some.")
            return

        accounts_text = "Your accounts:\n\n" + "\n".join([f"• {account}" for account in self.accounts])
        self.bot.reply_to(message, accounts_text)

    def add_account_command(self, message):
        """Command to add a new account"""
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        if self.is_first_time():
            self.bot.reply_to(message, "Please complete the initial setup first by using the /start command.")
            return

        msg = self.bot.reply_to(message, "What account would you like to add?")
        self.bot.register_next_step_handler(msg, self.process_add_account)

    def process_add_account(self, message):
        """Process the new account name"""
        if not self.is_authorized(message):
            return

        new_account = message.text.strip()

        if not new_account:
            self.bot.reply_to(message, "Account name cannot be empty.")
            return

        if new_account in self.accounts:
            self.bot.reply_to(message, f"Account '{new_account}' already exists.")
            return

        self.accounts.append(new_account)
        self.save_accounts(self.accounts)
        self.bot.reply_to(message, f"Account '{new_account}' added successfully!")

    def remove_account_command(self, message):
        """Command to remove an account"""
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        if self.is_first_time():
            self.bot.reply_to(message, "Please complete the initial setup first by using the /start command.")
            return

        if not self.accounts:
            self.bot.reply_to(message, "No accounts to remove.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = []

        for account in self.accounts:
            buttons.append(types.InlineKeyboardButton(
                text=account,
                callback_data=f"remove_acc_{account}"
            ))

        markup.add(*buttons)
        self.bot.send_message(
            message.chat.id,
            "Select an account to remove:",
            reply_markup=markup
        )

    def edit_account_command(self, message):
        """Command to edit an account name"""
        if not self.is_authorized(message):
            self.bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
            return

        if self.is_first_time():
            self.bot.reply_to(message, "Please complete the initial setup first by using the /start command.")
            return

        if not self.accounts:
            self.bot.reply_to(message, "No accounts to edit.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = []

        for account in self.accounts:
            buttons.append(types.InlineKeyboardButton(
                text=account,
                callback_data=f"edit_acc_{account}"
            ))

        markup.add(*buttons)
        self.bot.send_message(
            message.chat.id,
            "Select an account to edit:",
            reply_markup=markup
        )

    def setup_callback_handlers(self):
        """Setup callback handlers for this cog"""
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('onboard_'))
        def onboarding_callback(call):
            self.onboarding_callback_handler(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('remove_acc_'))
        def process_remove_account_callback(call):
            self.process_remove_account_callback_impl(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('edit_acc_'))
        def process_edit_account_callback(call):
            self.process_edit_account_callback_impl(call)

    def onboarding_callback_handler(self, call):
        """Handle callbacks during onboarding"""
        user_id = call.from_user.id

        if user_id != self.ALLOWED_USER_ID or user_id not in self.onboarding_data:
            return

        if call.data == "onboard_more_accounts":
            # Edit message to show selection
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Let's add another account. What would you like to call it?"
            )

            # Register next step handler
            self.bot.register_next_step_handler(call.message, self.process_onboarding_account)

        elif call.data == "onboard_complete":
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Great! Setting up your accounts..."
            )

            self.finish_onboarding(call.message)

    def process_remove_account_callback_impl(self, call):
        """Process the account removal selection"""
        user_id = call.from_user.id

        if user_id != self.ALLOWED_USER_ID:
            return

        # Extract account from callback data
        account_to_remove = call.data.replace('remove_acc_', '', 1)

        if account_to_remove in self.accounts:
            # Check if this is the last account
            if len(self.accounts) <= 1:
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Cannot remove the last account. You need at least one account."
                )
                return

            self.accounts.remove(account_to_remove)
            self.save_accounts(self.accounts)

            # Update expenses sheet
            updated_count = self.update_removed_account_in_excel(account_to_remove)

            message = f"Account '{account_to_remove}' has been removed."
            if updated_count > 0:
                message += f"\n\nWarning: {updated_count} expense entries used this account. These entries now have '[Deleted Account]' as their account."

            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=message
            )
        else:
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Account '{account_to_remove}' not found or already removed."
            )

    def update_removed_account_in_excel(self, removed_account):
        """Update all instances of removed_account in the expenses sheet"""
        updated_count = 0

        try:
            # Check if the Excel file exists
            if not os.path.exists(self.data_file):
                return updated_count

            # Read the Excel file, expenses sheet
            try:
                df = pd.read_excel(self.data_file, sheet_name="Expenses")

                # Check if the Account column exists
                if 'Account' not in df.columns:
                    return updated_count

                # Find all rows with the removed account and update them
                mask = df['Account'] == removed_account
                updated_count = mask.sum()

                if updated_count > 0:
                    df.loc[mask, 'Account'] = "[Deleted Account]"

                    # Save the updated dataframe back to the Excel file
                    with pd.ExcelWriter(self.data_file, mode='a', if_sheet_exists='replace') as writer:
                        df.to_excel(writer, sheet_name="Expenses", index=False)
            except Exception as e:
                print(f"Error updating expenses after account removal: {e}")

            return updated_count
        except Exception as e:
            print(f"Error processing Excel file: {e}")
            return updated_count

    def process_edit_account_callback_impl(self, call):
        """Process the account edit selection"""
        user_id = call.from_user.id

        if user_id != self.ALLOWED_USER_ID:
            return

        # Extract account from callback data
        account_to_edit = call.data.replace('edit_acc_', '', 1)

        if account_to_edit in self.accounts:
            # Store the account being edited
            self.edit_account_session[user_id] = account_to_edit

            # Edit message to show selected account
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"You are editing account: '{account_to_edit}'\nPlease enter the new name:"
            )

            # Register next step handler to get new account name
            self.bot.register_next_step_handler(call.message, self.process_new_account_name)
        else:
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Account '{account_to_edit}' not found."
            )

    def process_new_account_name(self, message):
        """Process the new account name"""
        if not self.is_authorized(message):
            return

        user_id = message.from_user.id

        # Get the old account name from session
        if user_id not in self.edit_account_session:
            self.bot.reply_to(message, "Session expired. Please try again.")
            return

        old_account = self.edit_account_session[user_id]
        new_account = message.text.strip()

        if not new_account:
            self.bot.reply_to(message, "Account name cannot be empty.")
            return

        if new_account in self.accounts and new_account != old_account:
            self.bot.reply_to(message, f"Account '{new_account}' already exists.")
            return

        # Update the account in the list
        index = self.accounts.index(old_account)
        self.accounts[index] = new_account
        self.save_accounts(self.accounts)

        # Update Excel sheet
        updated_count = self.update_account_in_excel(old_account, new_account)

        # Clean up session
        del self.edit_account_session[user_id]

        if updated_count > 0:
            self.bot.reply_to(message,
                              f"Account renamed from '{old_account}' to '{new_account}' successfully!\n"
                              f"Updated {updated_count} existing entries in the expense sheet.")
        else:
            self.bot.reply_to(message,
                              f"Account renamed from '{old_account}' to '{new_account}' successfully!\n"
                              f"No existing entries needed updating.")

    def update_account_in_excel(self, old_account, new_account):
        """Update all instances of old_account to new_account in the Excel file"""
        updated_count = 0

        try:
            # Check if the Excel file exists
            if not os.path.exists(self.data_file):
                return updated_count

            # Read the Excel file, expenses sheet
            try:
                df = pd.read_excel(self.data_file, sheet_name="Expenses")

                # Check if the Account column exists
                if 'Account' not in df.columns:
                    return updated_count

                # Find all rows with the old account and update them
                mask = df['Account'] == old_account
                updated_count = mask.sum()

                if updated_count > 0:
                    df.loc[mask, 'Account'] = new_account

                    # Save the updated dataframe back to the Excel file
                    with pd.ExcelWriter(self.data_file, mode='a', if_sheet_exists='replace') as writer:
                        df.to_excel(writer, sheet_name="Expenses", index=False)
            except Exception as e:
                print(f"Error updating expenses after account edit: {e}")

            return updated_count
        except Exception as e:
            print(f"Error processing Excel file: {e}")
            return updated_count
