"""
Discord WorkPause Bot.
"""

import discord
from discord.ext import commands
from utils.config_utils import get_settings

app_settings = get_settings()
intents = discord.Intents.default()
intents.message_content = True


class WorkPauseBot(commands.Bot):
    """A Discord bot for tracking work and pause sessions.

    Attributes:
        command_prefix (str): Prefix used for bot commands.
        intents (discord.Intents): The intents configuration for event handling.
    """

    async def setup_hook(self):
        """Set up the bot before it becomes ready."""

        await self.load_extension("routes.activity")


bot = WorkPauseBot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""

    await bot.tree.sync()
    print(f"✅ Bot is ready as {bot.user}")
    print("✅ Slash commands synced.")


def main():
    """Entry point for starting the Discord bot.

    Raises:
        ValueError: If the `DISCORD_BOT_TOKEN` is not found in environment settings.
    """

    if not app_settings.DISCORD_BOT_TOKEN:
        raise ValueError(
            "❌ No Discord bot token found. Set DISCORD_BOT_TOKEN in your .env file."
        )

    bot.run(app_settings.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
