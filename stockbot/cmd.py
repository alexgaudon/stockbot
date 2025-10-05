import yfinance as yf
from discord.ext import commands


@commands.command()
async def stock(ctx, symbol: str):
    """Get stock information for a given symbol."""
    try:
        stock = yf.Ticker(symbol.upper())
        info = stock.info
        price = info.get('currentPrice', 'N/A')
        name = info.get('longName', symbol.upper())
        message = f"{name} ({symbol.upper()}): ${price}"
        print(f"Sending message: {message}")
        await ctx.send(message)
    except Exception as e:
        error_message = f"Error fetching data for {symbol}: {str(e)}"
        print(f"Sending message: {error_message}")
        await ctx.send(error_message)


def setup(bot):
    bot.add_command(stock)