import os
import telebot
from dotenv import load_dotenv
from cogs.add import AddCommandCog
from cogs.categories import CategoriesCog
from cogs.accounts import AccountsCog

# Load environment variables from .env file
load_dotenv()

# Get sensitive information from environment variables
TOKEN = os.getenv("TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))  # Convert to integer

# Initialize the bot
bot = telebot.TeleBot(TOKEN)

# Help text
help_text = """
Welcome to your expense tracker bot!

*Expense Tracking Commands:*
/add - Add a new expense entry

*Account Management:*
/accounts - List all available accounts
/addaccount - Add a new account
/editaccount - Edit/rename an account
/removeaccount - Remove an account

*Category Management:*
/categories - List all available categories
/addcategory - Add a new category
/editcategory - Edit/rename a category
/removecategory - Remove a category

*General Commands:*
/start - Start the bot
/help - Show this help message
"""


# Start command handler
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id != ALLOWED_USER_ID:
        bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
        return

    # Check if this is the first time running the bot
    if accounts_cog.is_first_time():
        # Start onboarding process
        accounts_cog.start_onboarding(message)
    else:
        bot.reply_to(message, help_text, parse_mode="Markdown")


# Help command handler
@bot.message_handler(commands=['help'])
def help_command(message):
    if message.from_user.id != ALLOWED_USER_ID:
        return
    bot.reply_to(message, help_text, parse_mode="Markdown")


# Load cogs
def load_cogs():
    # Initialize the accounts cog first (for onboarding)
    accounts_cog = AccountsCog(bot, ALLOWED_USER_ID)
    # Initialize the categories cog
    categories_cog = CategoriesCog(bot, ALLOWED_USER_ID, defer_creation=accounts_cog.is_first_time())
    # Initialize the add command cog
    add_cog = AddCommandCog(bot, ALLOWED_USER_ID, categories_cog, accounts_cog)
    # Setup callback handlers after initialization
    accounts_cog.setup_callback_handlers()
    categories_cog.setup_callback_handlers()
    add_cog.setup_callback_handlers()

    return accounts_cog, categories_cog, add_cog


# Start the bot
if __name__ == "__main__":
    # Verify that environment variables were loaded
    if not TOKEN:
        print("Error: BOT_TOKEN not found in .env file")
        exit(1)
    if not ALLOWED_USER_ID:
        print("Error: ALLOWED_USER_ID not found in .env file")
        exit(1)

    # Load all cogs
    accounts_cog, categories_cog, cogs = load_cogs()

    print("Bot started successfully!")
    bot.polling(none_stop=True)
