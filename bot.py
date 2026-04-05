"""Cliente principal — painel Legião Espartan (100 funções via UI)."""

from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import Settings
from database import Database
from panel import get_logo_urls, install_panel, refresh_panel_message, register_panel_views

log = logging.getLogger(__name__)


class Asphalt9Bot(commands.Bot):
    def __init__(self, settings: Settings, database: Database) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = False
        super().__init__(command_prefix=commands.when_mentioned, intents=intents, help_command=None)
        self.settings = settings
        self.db = database

    async def setup_hook(self) -> None:
        await self.db.connect()
        register_panel_views(self)
        await self.load_extension("cogs.painel")
        guild = discord.Object(id=self.settings.guild_id) if self.settings.guild_id else None
        synced = await self.tree.sync(guild=guild) if guild else await self.tree.sync()
        log.info("Slash sincronizados: %s", len(synced))
        self.loop.create_task(self._logo_cycle())

    async def _logo_cycle(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await asyncio.sleep(self.settings.logo_cycle_seconds)
                for g in list(self.guilds):
                    if self.settings.guild_id and g.id != self.settings.guild_id:
                        continue
                    urls = await get_logo_urls(self, g.id)
                    if len(urls) > 1:
                        await refresh_panel_message(self, g)
            except Exception:
                log.exception("Ciclo do logo / painel")

    async def on_ready(self) -> None:
        assert self.user
        log.info("Logado como %s (%s)", self.user, self.user.id)
        if self.settings.guild_id and self.settings.panel_channel_id:
            guild = self.get_guild(self.settings.guild_id)
            if guild:
                mid = await self.db.get_panel_message_id(guild.id)
                if mid is None:
                    await install_panel(self, guild)

    async def close(self) -> None:
        await self.db.close()
        await super().close()
