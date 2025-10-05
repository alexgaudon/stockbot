import yfinance as yf
import discord
import re

class StockBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        await self.handle_ticker_patterns(message)

    async def handle_ticker_patterns(self, message):
        if message.content.startswith('!'):
            return

        patterns = [p.strip() for p in re.findall(r"\[\[\[(.*?)\]\]\]", message.content)]
        if not patterns:
            return

        replies = []
        for pattern in patterns:
            if pattern.startswith('?'):
                query = pattern[1:].strip()
                if not query:
                    replies.append("Please provide a search term after [[[?search]]].")
                    continue
                replies.append(await self.search_yahoo_finance(query))
            else:
                replies.append(await self.get_stock_info_with_search(pattern.upper()))

        if replies:
            await message.channel.send("\n\n".join(replies))

    async def search_yahoo_finance(self, query):
        import aiohttp
        from urllib.parse import quote

        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={quote(query)}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return f"Failed to search Yahoo Finance for: {query} (status: {resp.status})"
                    data = await resp.json()
                    quotes = data.get("quotes", [])
                    if not quotes:
                        return f"No tickers found for search: {query}"
                    results = [
                        f"{q.get('symbol', '')}: {q.get('shortname') or q.get('longname', '')}"
                        for q in quotes[:5]
                    ]
                    response = "Search results:\n" + "\n".join(results)
                    print(f"Sending message: {response}")
                    return response
        except Exception as e:
            error_message = f"Error searching for '{query}': {e}"
            print(f"Sending message: {error_message}")
            return error_message

    async def get_stock_info_with_search(self, symbol):
        # Try to get stock info, and if not found, search for it
        info, error = await self._try_get_stock_info(symbol)
        if info is not None:
            return info
        # If not found, search for the symbol
        search_result = await self.search_yahoo_finance(symbol)
        return f"Could not find stock info for '{symbol}'.\n{search_result}"

    async def _try_get_stock_info(self, symbol):
        try:
            stock = yf.Ticker(symbol)
            info = stock.info

            # Check if info is valid and has a price
            price = (
                info.get('currentPrice')
                or info.get('regularMarketPrice')
                or info.get('previousClose')
            )
            if price is None:
                hist = stock.history(period='1d')
                price = hist['Close'].iloc[-1] if not hist.empty else None

            # If still no price and no name, treat as not found
            if (price is None) and not (info.get('longName') or info.get('shortName')):
                return None, f"Stock not found for symbol: {symbol}"

            price_str = f"{price:.2f}" if price is not None else "N/A"
            name = info.get('longName') or info.get('shortName') or symbol
            currency = info.get('currency', 'USD')

            response = f"{name} ({symbol}): {currency} {price_str}"
            print(f"Sending message: {response}")
            return response, None
        except Exception as e:
            error_message = f"Error fetching data for {symbol}: {e}"
            print(f"Sending message: {error_message}")
            return None, error_message
