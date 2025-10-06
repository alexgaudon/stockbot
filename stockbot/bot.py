import discord
from stockbot.command_handler import CommandHandler
from stockbot.commands import TickerPatternCommand
from stockbot.stock_service import StockService

class StockBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.stock_service = StockService()
        self.command_handler = CommandHandler()
        self.command_handler.register(TickerPatternCommand(self.stock_service))

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author.bot or message.author == self.user:
            return

        await self.command_handler.execute(message)
