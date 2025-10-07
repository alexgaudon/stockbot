import discord
from stockbot.command_handler import CommandHandler
from stockbot.commands import MinimalTickerCommand, TickerWithPeriodCommand, TickerCommand
from stockbot.stock_service import StockService

class StockBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.stock_service = StockService()
        self.command_handler = CommandHandler()
        # Register specialized commands in priority order (more specific first)
        self.command_handler.register(MinimalTickerCommand(self.stock_service))
        self.command_handler.register(TickerWithPeriodCommand(self.stock_service))
        self.command_handler.register(TickerCommand(self.stock_service))

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author.bot or message.author == self.user:
            return

        await self.command_handler.execute(message)
