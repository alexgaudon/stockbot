import yfinance as yf
import discord
import re
import matplotlib.pyplot as plt
import io
import pandas as pd
from datetime import datetime, timedelta

class StockBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author == self.user:
            return
        await self.handle_ticker_patterns(message)

    async def handle_ticker_patterns(self, message):
        if message.content.startswith('!'):
            return

        patterns = [p.strip() for p in re.findall(r"\[\[\[(.*?)\]\]\]", message.content)]
        if not patterns:
            return

        # Deduplicate patterns while preserving order
        # For tickers, treat case-insensitively; for searches, case-sensitive
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            # Create a key for deduplication
            if pattern.startswith('?'):
                # Search queries: deduplicate case-insensitively
                key = pattern.lower()
            else:
                # Stock tickers: extract symbol (before comma) and deduplicate case-insensitively
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
                    embed = await self.search_yahoo_finance(query)
                    embeds_and_files.append((embed, None))
                else:
                    parts = pattern.upper().split(',', 1)
                    symbol = parts[0]
                    period_str = parts[1] if len(parts) > 1 else '3'
                    try:
                        period = int(period_str)
                    except ValueError:
                        period = 3
                    embed, file = await self.get_stock_info_with_search(symbol, period)
                    embeds_and_files.append((embed, file))

            for embed, file in embeds_and_files:
                await message.channel.send(embed=embed, file=file)

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
                        embed = discord.Embed(
                            title="Yahoo Finance Search Failed",
                            description=f"Failed to search Yahoo Finance for: `{query}` (status: {resp.status})",
                            color=discord.Color.red()
                        )
                        return embed
                    data = await resp.json()
                    quotes = data.get("quotes", [])
                    if not quotes:
                        embed = discord.Embed(
                            title="No Results",
                            description=f"No tickers found for search: `{query}`",
                            color=discord.Color.orange()
                        )
                        return embed
                    embed = discord.Embed(
                        title=f"Search results for '{query}'",
                        color=discord.Color.blue()
                    )
                    for q in quotes[:5]:
                        symbol = q.get('symbol', '')
                        name = q.get('shortname') or q.get('longname', '')
                        embed.add_field(name=symbol, value=name or "No name", inline=False)
                    return embed
        except Exception as e:
            error_message = f"Error searching for '{query}': {e}"
            embed = discord.Embed(
                title="Error",
                description=error_message,
                color=discord.Color.red()
            )
            return embed

    async def get_stock_info_with_search(self, symbol, period=3):
        # Try to get stock info, and if not found, search for it
        embed, file = await self._try_get_stock_info(symbol, period)
        if embed is not None:
            return embed, file
        # If not found, search for the symbol
        search_embed = await self.search_yahoo_finance(symbol)
        not_found_embed = discord.Embed(
            title="Stock Not Found",
            description=f"Could not find stock info for '{symbol}'.",
            color=discord.Color.orange()
        )
        # Return both not found and search result as a single embed with extra info
        # But since Discord only allows one embed per return, we can add search results as fields
        if search_embed and search_embed.fields:
            for field in search_embed.fields:
                not_found_embed.add_field(name=field.name, value=field.value, inline=False)
        return not_found_embed, None

    async def _try_get_stock_info(self, symbol, period=3):
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
                return None, None

            price_str = f"{price:.2f}" if price is not None else "N/A"
            name = info.get('longName') or info.get('shortName') or symbol
            currency = info.get('currency', 'USD')
            exchange = info.get('exchange', 'Unknown')
            website = info.get('website')

            # Calculate daily % change
            percent_change = None
            prev_close = info.get('previousClose')
            if price is not None and prev_close is not None and prev_close != 0:
                percent_change = ((price - prev_close) / prev_close) * 100

            percent_change_str = f"{percent_change:+.2f}%" if percent_change is not None else "N/A"

            # Calculate returns for 1 month, 3 months, 12 months
            returns = {}
            now = datetime.now()
            periods = {
                "1 Month Return": 30,
                "3 Month Return": 90,
                "12 Month Return": 365
            }
            try:
                # Download up to 13 months of daily data for all return calculations
                hist = stock.history(period="400d")
                if not hist.empty and 'Close' in hist.columns:
                    last_close = hist['Close'].iloc[-1]
                    for label, days in periods.items():
                        # Find the closest trading day to the target date
                        target_date = now - timedelta(days=days)
                        # Find the row in hist with index <= target_date
                        # hist.index is tz-aware, so convert target_date to same tz if needed
                        if hasattr(hist.index[0], 'tzinfo') and hist.index[0].tzinfo is not None:
                            target_date = target_date.replace(tzinfo=hist.index[0].tzinfo)
                        # Find the closest date in the past
                        past_prices = hist[hist.index <= pd.Timestamp(target_date)]
                        if not past_prices.empty:
                            past_close = past_prices['Close'].iloc[-1]
                            if past_close != 0:
                                ret = ((last_close - past_close) / past_close) * 100
                                returns[label] = f"{ret:+.2f}%"
                            else:
                                returns[label] = "N/A"
                        else:
                            returns[label] = "N/A"
                else:
                    for label in periods:
                        returns[label] = "N/A"
            except Exception:
                for label in periods:
                    returns[label] = "N/A"

            embed = discord.Embed(
                title=f"{name} ({symbol})",
                color=discord.Color.green()
            )
            embed.add_field(name="Price", value=f"{currency} {price_str}", inline=True)
            embed.add_field(name="Exchange", value=exchange, inline=True)
            if website:
                embed.add_field(name="Website", value=website, inline=False)
            embed.add_field(name="Daily % Change", value=percent_change_str, inline=True)
            # Add returns
            for label in ["1 Month Return", "3 Month Return", "12 Month Return"]:
                embed.add_field(name=label, value=returns.get(label, "N/A"), inline=True)

            # Generate chart
            file = None
            try:
                hist_chart = stock.history(period=f'{period}mo')
                if not hist_chart.empty:
                    plt.figure(figsize=(10,5))
                    plt.plot(hist_chart.index, hist_chart['Close'])
                    plt.title(f'{symbol} Price Over {period} Months')
                    plt.xlabel('Date')
                    plt.ylabel(f'Price ({currency})')
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    file = discord.File(buf, filename='chart.png')
                    embed.set_image(url='attachment://chart.png')
                    plt.close()
            except Exception:
                pass  # If chart fails, just skip

            return embed, file
        except Exception as e:
            error_message = f"Error fetching data for {symbol}: {e}"
            embed = discord.Embed(
                title="Error",
                description=error_message,
                color=discord.Color.red()
            )
            return embed, None
