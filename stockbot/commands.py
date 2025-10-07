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


class MinimalTickerCommand(Command):
    def __init__(self, stock_service: StockService):
        super().__init__("minimal_ticker")
        self.stock_service = stock_service

    def matches(self, message: Message) -> bool:
        if message.content.startswith('!'):
            return False
        # Match triple brackets content starting with a dash: [[[-SYMBOL]]]
        return re.search(r"\[\[\[\s*-\s*([A-Za-z0-9\.-]+)\s*\]\]\]", message.content) is not None

    async def execute(self, message: Message) -> None:
        if not self.matches(message):
            return

        patterns = [p.strip() for p in re.findall(r"\[\[\[(.*?)\]\]\]", message.content)]
        minimal_symbols = []
        for pattern in patterns:
            if pattern.strip().startswith('-'):
                sym = pattern.strip()[1:].strip()
                # stop at comma if any extraneous parameters were provided
                sym = sym.split(',', 1)[0].strip()
                if sym:
                    minimal_symbols.append(sym.upper())

        # Deduplicate
        minimal_symbols = list(dict.fromkeys(minimal_symbols))

        if not minimal_symbols:
            return

        async with message.channel.typing():
            for symbol in minimal_symbols:
                embed, _ = await self.stock_service.get_stock_brief_with_search(symbol)
                await message.channel.send(embed=embed)


class TickerWithPeriodCommand(Command):
    def __init__(self, stock_service: StockService):
        super().__init__("ticker_with_period")
        self.stock_service = stock_service

    def matches(self, message: Message) -> bool:
        if message.content.startswith('!'):
            return False
        # Contains a triple-bracket pattern with a comma and not starting with '?' or '-'
        for raw in re.findall(r"\[\[\[(.*?)\]\]\]", message.content):
            stripped = raw.strip()
            if not stripped.startswith('?') and not stripped.startswith('-') and ',' in stripped:
                return True
        return False

    async def execute(self, message: Message) -> None:
        if not self.matches(message):
            return

        patterns = [p.strip() for p in re.findall(r"\[\[\[(.*?)\]\]\]", message.content)]

        seen = set()
        unique = []
        for pattern in patterns:
            stripped = pattern.strip()
            if stripped.startswith('?') or stripped.startswith('-'):
                continue
            if ',' not in stripped:
                continue
            symbol = stripped.split(',', 1)[0].upper()
            if symbol not in seen:
                seen.add(symbol)
                unique.append(stripped)

        if not unique:
            return

        async with message.channel.typing():
            for pattern in unique:
                parts = pattern.upper().split(',', 1)
                symbol = parts[0]
                period_str = parts[1]
                try:
                    period = int(period_str)
                except ValueError:
                    period = 3
                embed, file = await self.stock_service.get_stock_info_with_search(
                    symbol,
                    chart_period_months=period
                )
                await message.channel.send(embed=embed, file=file)


class TickerCommand(Command):
    def __init__(self, stock_service: StockService):
        super().__init__("ticker")
        self.stock_service = stock_service

    def matches(self, message: Message) -> bool:
        if message.content.startswith('!'):
            return False
        # Match either [[[?query]]] or plain [[[SYMBOL]]] without comma and not starting with '-'
        for raw in re.findall(r"\[\[\[(.*?)\]\]\]", message.content):
            stripped = raw.strip()
            if stripped.startswith('?'):
                return True
            if not stripped.startswith('-') and ',' not in stripped and stripped != '':
                return True
        return False

    async def execute(self, message: Message) -> None:
        if not self.matches(message):
            return

        patterns = [p.strip() for p in re.findall(r"\[\[\[(.*?)\]\]\]", message.content)]

        queries: list[str] = []
        symbols: list[str] = []

        for pattern in patterns:
            stripped = pattern.strip()
            if stripped.startswith('?'):
                q = stripped[1:].strip()
                if q:
                    queries.append(q)
            elif not stripped.startswith('-') and ',' not in stripped and stripped:
                symbols.append(stripped.split()[0].upper())

        # Deduplicate preserving order
        queries = list(dict.fromkeys(queries))
        symbols = list(dict.fromkeys(symbols))

        if not queries and not symbols:
            return

        async with message.channel.typing():
            for query in queries:
                embed = await self.stock_service.search_ticker(query)
                await message.channel.send(embed=embed)

            for symbol in symbols:
                embed, file = await self.stock_service.get_stock_info_with_search(symbol)
                await message.channel.send(embed=embed, file=file)