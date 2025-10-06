from abc import ABC, abstractmethod
from discord import Message
import discord
import re
from stockbot.stock_service import StockService


class Command(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, message: Message) -> None:
        pass

    @abstractmethod
    def matches(self, message: Message) -> bool:
        pass


class TickerPatternCommand(Command):
    def __init__(self, stock_service: StockService):
        super().__init__("ticker_pattern")
        self.stock_service = stock_service

    def matches(self, message: Message) -> bool:
        if message.content.startswith('!'):
            return False
        return re.search(r"\[\[\[(.*?)\]\]\]", message.content) is not None

    async def execute(self, message: Message) -> None:
        if not self.matches(message):
            return

        patterns = [p.strip() for p in re.findall(r"\[\[\[(.*?)\]\]\]", message.content)]
        if not patterns:
            return

        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern.startswith('?'):
                key = pattern.lower()
            else:
                symbol = pattern.split(',', 1)[0].upper()
                key = symbol
            
            if key not in seen:
                seen.add(key)
                unique_patterns.append(pattern)

        async with message.channel.typing():
            embeds_and_files = []
            for pattern in unique_patterns:
                if pattern.startswith('?'):
                    query = pattern[1:].strip()
                    if not query:
                        embed = discord.Embed(
                            title="Missing Search Term",
                            description="Please provide a search term after [[[?search]]].",
                            color=discord.Color.red()
                        )
                        embeds_and_files.append((embed, None))
                        continue
                    embed = await self.stock_service.search_ticker(query)
                    embeds_and_files.append((embed, None))
                else:
                    parts = pattern.upper().split(',', 1)
                    symbol = parts[0]
                    period_str = parts[1] if len(parts) > 1 else '3'
                    try:
                        period = int(period_str)
                    except ValueError:
                        period = 3

                    embed, file = await self.stock_service.get_stock_info_with_search(
                        symbol, 
                        chart_period_months=period
                    )
                    
                    embeds_and_files.append((embed, file))

            for embed, file in embeds_and_files:
                await message.channel.send(embed=embed, file=file)