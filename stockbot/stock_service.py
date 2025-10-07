import yfinance as yf
import matplotlib.pyplot as plt
import io
import pandas as pd
import discord
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List


class StockService:
    """Service for fetching and processing stock data"""
    
    async def search_ticker(self, query: str) -> discord.Embed:
        """Search for tickers on Yahoo Finance"""
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

    def calculate_period_returns(self, symbol: str, periods_months: List[int]) -> Dict[int, Optional[float]]:
        """
        Calculate percentage returns for multiple periods
        
        Args:
            symbol: Stock ticker symbol
            periods_months: List of periods in months (e.g., [1, 3, 9, 12])
            
        Returns:
            Dictionary mapping period (in months) to percentage return
        """
        try:
            stock = yf.Ticker(symbol)
            # Download sufficient historical data (400 days covers up to 13 months)
            hist = stock.history(period="400d")
            
            if hist.empty or 'Close' not in hist.columns:
                return {period: None for period in periods_months}
            
            returns = {}
            last_close = hist['Close'].iloc[-1]
            now = datetime.now()
            
            for period_months in periods_months:
                days = period_months * 30  # Approximate days in a month
                target_date = now - timedelta(days=days)
                
                # Handle timezone-aware datetime
                if hasattr(hist.index[0], 'tzinfo') and hist.index[0].tzinfo is not None:
                    target_date = target_date.replace(tzinfo=hist.index[0].tzinfo)
                
                # Find the closest trading day in the past
                past_prices = hist[hist.index <= pd.Timestamp(target_date)]
                if not past_prices.empty:
                    past_close = past_prices['Close'].iloc[-1]
                    if past_close != 0:
                        ret = ((last_close - past_close) / past_close) * 100
                        returns[period_months] = ret
                    else:
                        returns[period_months] = None
                else:
                    returns[period_months] = None
            
            return returns
        except Exception:
            return {period: None for period in periods_months}

    async def get_stock_info(
        self, 
        symbol: str, 
        chart_period_months: int = 3,
        return_periods: Optional[List[int]] = None
    ) -> Tuple[Optional[discord.Embed], Optional[discord.File]]:
        """
        Get comprehensive stock information including price, returns, and chart
        
        Args:
            symbol: Stock ticker symbol
            chart_period_months: Period for the price chart in months
            return_periods: List of periods (in months) to calculate returns for.
                          Defaults to [1, 3, 12] if not specified.
        
        Returns:
            Tuple of (embed, file) where file is the chart image
        """
        if return_periods is None:
            return_periods = [1, 3, 12]
        
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

            # Calculate returns for specified periods
            returns = self.calculate_period_returns(symbol, return_periods)

            # Create embed
            embed = discord.Embed(
                title=f"{name} ({symbol})",
                color=discord.Color.green()
            )
            embed.add_field(name="Price", value=f"{currency} {price_str}", inline=True)
            embed.add_field(name="Exchange", value=exchange, inline=True)
            if website:
                embed.add_field(name="Website", value=website, inline=False)
            embed.add_field(name="Daily % Change", value=percent_change_str, inline=True)
            
            # Add returns for each period
            for period_months in sorted(return_periods):
                label = f"{period_months} Month Return" if period_months > 1 else "1 Month Return"
                ret_value = returns.get(period_months)
                ret_str = f"{ret_value:+.2f}%" if ret_value is not None else "N/A"
                embed.add_field(name=label, value=ret_str, inline=True)

            # Generate chart
            file = None
            try:
                hist_chart = stock.history(period=f'{chart_period_months}mo')
                if not hist_chart.empty:
                    plt.figure(figsize=(10, 5))
                    plt.plot(hist_chart.index, hist_chart['Close'])
                    plt.title(f'{symbol} Price Over {chart_period_months} Months')
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

    async def get_stock_info_with_search(
        self, 
        symbol: str, 
        chart_period_months: int = 3,
        return_periods: Optional[List[int]] = None
    ) -> Tuple[discord.Embed, Optional[discord.File]]:
        """
        Get stock info, and if not found, search for similar tickers
        
        Args:
            symbol: Stock ticker symbol
            chart_period_months: Period for the price chart in months
            return_periods: List of periods (in months) to calculate returns for
        
        Returns:
            Tuple of (embed, file)
        """
        embed, file = await self.get_stock_info(symbol, chart_period_months, return_periods)
        
        if embed is not None:
            return embed, file
        
        # If not found, search for the symbol
        search_embed = await self.search_ticker(symbol)
        not_found_embed = discord.Embed(
            title="Stock Not Found",
            description=f"Could not find stock info for '{symbol}'.",
            color=discord.Color.orange()
        )
        
        # Add search results as fields
        if search_embed and search_embed.fields:
            for field in search_embed.fields:
                not_found_embed.add_field(name=field.name, value=field.value, inline=False)
        
        return not_found_embed, None

    async def get_stock_brief(self, symbol: str) -> Tuple[Optional[discord.Embed], Optional[discord.File]]:
        """
        Get a minimal stock embed with just price and daily percent change.
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info

            price = (
                info.get('currentPrice')
                or info.get('regularMarketPrice')
                or info.get('previousClose')
            )

            if price is None:
                hist = stock.history(period='1d')
                price = hist['Close'].iloc[-1] if not hist.empty else None

            if (price is None) and not (info.get('longName') or info.get('shortName')):
                return None, None

            name = info.get('longName') or info.get('shortName') or symbol
            currency = info.get('currency', 'USD')

            percent_change = None
            prev_close = info.get('previousClose')
            if price is not None and prev_close is not None and prev_close != 0:
                percent_change = ((price - prev_close) / prev_close) * 100

            price_str = f"{currency} {price:.2f}" if price is not None else "N/A"
            percent_change_str = f"{percent_change:+.2f}%" if percent_change is not None else "N/A"

            embed = discord.Embed(
                title=f"{name} ({symbol})",
                color=discord.Color.green()
            )
            embed.add_field(name="Price", value=price_str, inline=True)
            embed.add_field(name="Daily % Change", value=percent_change_str, inline=True)

            return embed, None
        except Exception as e:
            error_message = f"Error fetching data for {symbol}: {e}"
            embed = discord.Embed(
                title="Error",
                description=error_message,
                color=discord.Color.red()
            )
            return embed, None

    async def get_stock_brief_with_search(self, symbol: str) -> Tuple[discord.Embed, Optional[discord.File]]:
        """
        Get minimal stock info, and if not found, search for similar tickers.
        """
        embed, file = await self.get_stock_brief(symbol)

        if embed is not None:
            return embed, file

        search_embed = await self.search_ticker(symbol)
        not_found_embed = discord.Embed(
            title="Stock Not Found",
            description=f"Could not find stock info for '{symbol}'.",
            color=discord.Color.orange()
        )

        if search_embed and search_embed.fields:
            for field in search_embed.fields:
                not_found_embed.add_field(name=field.name, value=field.value, inline=False)

        return not_found_embed, None

