import os
import telebot
from dotenv import load_dotenv
from cogs.add import AddCommandCog
from cogs.categories import CategoriesCog

# Load environment variables from .env file
load_dotenv()

# Get sensitive information from environment variables
TOKEN = os.getenv("TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))  # Convert to integer

# Initialize the bot
bot = telebot.TeleBot(TOKEN)


# Start command handler - kept in main file
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id != ALLOWED_USER_ID:
        bot.reply_to(message, "Sorry, you're not authorized to use this bot.")
        return

    bot.reply_to(message, "Welcome to your expense tracker bot! Use /add to add a new expense.")


# Help command handler - kept in main file
@bot.message_handler(commands=['help'])
def help_command(message):
    if message.from_user.id != ALLOWED_USER_ID:
        return

    help_text = """
    *Expense Tracking Commands:*
    /add - Add a new expense entry

*Category Management:*
    /categories - List all available categories
    /addcategory - Add a new category
    /editcategory - Edit/rename a category
    /removecategory - Remove a category

*General Commands:*
    /start - Start the bot
    /help - Show this help message
    """
    bot.reply_to(message, help_text, parse_mode="Markdown")


# Load cogs
def load_cogs():
    # Initialize the categories cog first
    categories_cog = CategoriesCog(bot, ALLOWED_USER_ID)
    # Initialize the add command cog
    add_cog = AddCommandCog(bot, ALLOWED_USER_ID, categories_cog)
    # Setup callback handlers after initialization
    categories_cog.setup_callback_handlers()
    add_cog.setup_callback_handlers()

    return categories_cog, add_cog


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
    categories_cog, cogs = load_cogs()

    print("Bot started successfully!")
    bot.polling(none_stop=True)
