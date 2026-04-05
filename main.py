"""Ponto de entrada — hospedagem Discloud: `python main.py`."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone

import discord
from discord import app_commands

from bot import Asphalt9Bot
from config import load_settings
from database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("main")


async def reminder_loop(bot: Asphalt9Bot) -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now(timezone.utc).isoformat()
            due = await bot.db.due_reminders(now)
            for r in due:
                ch = bot.get_channel(int(r["channel_id"]))
                if isinstance(ch, discord.TextChannel):
                    msg = f"<@{r['author_id']}> **Lembrete:** {r['message']}"
                    await ch.send(msg[:2000])
                await bot.db.reminder_delete(int(r["id"]))
        except Exception:
            log.exception("Erro no loop de lembretes")
        await asyncio.sleep(30)


async def main() -> None:
    settings = load_settings()
    if not settings.token:
        log.error("Defina DISCORD_TOKEN (e na Discloud nas variáveis do app).")
        sys.exit(1)
    if not settings.guild_id or not settings.panel_channel_id:
        log.warning(
            "Recomendado: DISCORD_GUILD_ID e PANEL_CHANNEL_ID para instalar o painel automaticamente."
        )

    db = Database()
    bot = Asphalt9Bot(settings, db)

    @bot.tree.error
    async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        log.exception("Erro slash: %s", error)
        msg = "Erro ao executar."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    asyncio.create_task(reminder_loop(bot))
    await bot.start(settings.token)


if __name__ == "__main__":
    asyncio.run(main())
