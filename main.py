"""Ponto de entrada: Asphalt 9 Club Manager para Discord."""

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
        log.error("Defina DISCORD_TOKEN no arquivo .env (veja .env.example).")
        sys.exit(1)

    db = Database()
    bot = Asphalt9Bot(settings, db)

    @bot.event
    async def on_ready() -> None:
        log.info("Logado como %s (%s)", bot.user, bot.user.id if bot.user else "?")

    @bot.tree.error
    async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        log.exception("Erro em comando slash: %s", error)
        msg = "Ocorreu um erro ao executar o comando."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    asyncio.create_task(reminder_loop(bot))
    await bot.start(settings.token)


if __name__ == "__main__":
    asyncio.run(main())
