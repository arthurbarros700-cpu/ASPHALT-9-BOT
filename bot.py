"""Cliente principal do bot Asphalt 9 Club."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from config import Settings
from database import Database

log = logging.getLogger(__name__)


class Asphalt9Bot(commands.Bot):
    def __init__(self, settings: Settings, database: Database) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = False
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.settings = settings
        self.db = database

    async def setup_hook(self) -> None:
        await self.db.connect()
        cogs = [
            "cogs.meta",
            "cogs.club",
            "cogs.members",
            "cogs.reputation",
            "cogs.events",
            "cogs.moderation",
            "cogs.recruitment",
            "cogs.goals",
            "cogs.garage",
            "cogs.engagement",
            "cogs.competitive",
            "cogs.admin",
        ]
        for ext in cogs:
            await self.load_extension(ext)
        guild = discord.Object(id=self.settings.guild_id) if self.settings.guild_id else None
        synced = await self.tree.sync(guild=guild) if guild else await self.tree.sync()
        log.info("Comandos slash sincronizados: %s", len(synced))

    async def close(self) -> None:
        await self.db.close()
        await super().close()
