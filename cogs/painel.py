"""Único comando slash: abre o painel (uso interno staff). O servidor usa o painel fixo no canal."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from panel import LegionHomeView, current_thumbnail_url, panel_embed
from permissions import ensure_staff

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class PainelCog(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="painel", description="[Staff] Envia o painel Legião neste canal (recuperação).")
    async def painel(self, interaction: discord.Interaction) -> None:
        if not await ensure_staff(interaction):
            return
        if not interaction.guild:
            await interaction.response.send_message("Use em um servidor.", ephemeral=True)
            return
        logo = await current_thumbnail_url(self.bot, interaction.guild.id)
        emb = panel_embed(self.bot, interaction.guild, logo)
        await interaction.response.send_message(embed=emb, view=LegionHomeView(self.bot), ephemeral=False)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(PainelCog(bot))
