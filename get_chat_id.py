import os
import sys
import asyncio
from dotenv import load_dotenv

try:
    from telegram import Bot
except ImportError:
    print("Error: python-telegram-bot not installed!")
    print("   Install it with: pip install python-telegram-bot")
    sys.exit(1)

def load_bot_token():
    load_dotenv()
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        print("Bot token not found in .env file")
        bot_token = input("Please enter your Telegram Bot Token: ").strip()

        if not bot_token:
            print("Bot token is required!")
            sys.exit(1)

    return bot_token

async def get_chat_id(bot_token):
    try:
        bot = Bot(token=bot_token)

        print("Connecting to Telegram Bot...")

        bot_info = await bot.get_me()
        print(f"Connected to bot: @{bot_info.username}")
        print(f"   Bot Name: {bot_info.first_name}")

        print("\nFetching recent messages...")
        updates = await bot.get_updates()

        if not updates:
            print("\nNo messages found!")
            print("\nTo get your Chat ID:")
            print("   1. Open Telegram and find your bot")
            print("   2. Send any message to your bot (e.g., 'hello')")
            print("   3. Run this script again")
            return

        print(f"\nFound {len(updates)} message(s)")
        print("\n" + "="*50)
        print("CHAT ID INFORMATION")
        print("="*50)

        chat_ids = set()
        for update in updates:
            if update.message and update.message.chat:
                chat = update.message.chat
                chat_ids.add(chat.id)

                print(f"\nChat ID: {chat.id}")
                print(f"   Chat Type: {chat.type}")

                if chat.type == 'private':
                    print(f"   User: {chat.first_name or 'N/A'} {chat.last_name or ''}".strip())
                    if chat.username:
                        print(f"   Username: @{chat.username}")
                elif chat.type in ['group', 'supergroup']:
                    print(f"   Group: {chat.title}")

                if update.message.text:
                    preview = update.message.text[:50]
                    if len(update.message.text) > 50:
                        preview += "..."
                    print(f"   Last Message: {preview}")

        print("\n" + "="*50)

        if len(chat_ids) == 1:
            chat_id = list(chat_ids)[0]
            print(f"YOUR CHAT ID: {chat_id}")
            print(f"\nAdd this to your .env file:")
            print(f"   TELEGRAM_CHAT_ID={chat_id}")
        else:
            print("Multiple chats found. Use the Chat ID for your personal chat with the bot.")

        print("\nChat ID retrieval complete!")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("   - Check if your bot token is correct")
        print("   - Make sure you've sent at least one message to your bot")
        print("   - Verify your internet connection")

async def main():
    print("PortalPlus - Telegram Chat ID Finder")
    print("="*40)

    try:
        bot_token = load_bot_token()
        await get_chat_id(bot_token)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AttributeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
