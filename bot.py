import json
import logging
import os
import platform
import random
import sys

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv

load_dotenv()

# Setup bot intents
intents = discord.Intents.default()
# Enable message_content if you want to use prefix commands
intents.message_content = True  

# Logging setup
class LoggingFormatter(logging.Formatter):
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("PREFIX", "!")),
            intents=intents,
            help_command=None,
        )
        self.logger = logger
        self.bot_prefix = os.getenv("PREFIX", "!")
        self.invite_link = os.getenv("INVITE_LINK")

    async def load_cogs(self) -> None:
        for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    self.logger.info(f"Loaded extension '{extension}'")
                except Exception as e:
                    self.logger.error(f"Failed to load extension {extension}: {e}")

    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        statuses = ["with you!", "with Krypton!", "with humans!"]
        await self.change_presence(activity=discord.Game(random.choice(statuses)))

    @status_task.before_loop
    async def before_status_task(self) -> None:
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        self.logger.info(f"Logged in as {self.user}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        self.logger.info("-------------------")
        await self.load_cogs()
        self.status_task.start()

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        executed_command = context.command.qualified_name
        if context.guild:
            self.logger.info(
                f"Executed {executed_command} in {context.guild.name} by {context.author}"
            )
        else:
            self.logger.info(f"Executed {executed_command} in DMs by {context.author}")

    async def on_command_error(self, context: Context, error) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            embed = discord.Embed(
                description=f"Please slow down! Try again in {int(minutes)}m {int(seconds)}s.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            await context.send(embed=discord.Embed(
                description="You are not the owner of the bot!", color=0xE02B2B
            ))
        elif isinstance(error, commands.MissingPermissions):
            await context.send(embed=discord.Embed(
                description=f"You are missing: {', '.join(error.missing_permissions)}", 
                color=0xE02B2B
            ))
        elif isinstance(error, commands.BotMissingPermissions):
            await context.send(embed=discord.Embed(
                description=f"I am missing: {', '.join(error.missing_permissions)}",
                color=0xE02B2B,
            ))
        elif isinstance(error, commands.MissingRequiredArgument):
            await context.send(embed=discord.Embed(
                title="Error!",
                description=str(error).capitalize(),
                color=0xE02B2B,
            ))
        else:
            raise error


bot = DiscordBot()
bot.run(os.getenv("TOKEN"))