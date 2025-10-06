from stockbot.commands import Command
from discord import Message


class CommandHandler:
    def __init__(self):
        self.commands: list[Command] = []

    def register(self, command: Command) -> None:
        if any(cmd.name == command.name for cmd in self.commands):
            raise ValueError(f"Command {command.name} already registered")
        
        self.commands.append(command)

    async def execute(self, message: Message) -> None:
        for command in self.commands:
            if command.matches(message):
                await command.execute(message)