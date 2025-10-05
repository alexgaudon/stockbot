from pydantic_settings import BaseSettings


class Config(BaseSettings):
    discord_token: str

    class Config:
        env_file = ".env"


config = Config()