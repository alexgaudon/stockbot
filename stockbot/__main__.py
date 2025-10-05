from .bot import StockBot
from .config import config


def main():
    if not config.discord_token:
        raise ValueError("DISCORD_TOKEN environment variable is required. Create a .env file with discord_token = 'your_token_here'")
    bot = StockBot()
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()