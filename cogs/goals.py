"""Metas de clube (REP, eventos, etc.)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Goals(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="meta_criar", description="Cria meta coletiva para o clube.")
    @staff_only()
    @app_commands.describe(
        titulo="Nome da meta",
        alvo="Valor alvo numérico",
        unidade="rep | eventos | vitórias | custom",
        prazo_iso="Prazo opcional em ISO",
    )
    async def meta_criar(
        self,
        interaction: discord.Interaction,
        titulo: str,
        alvo: app_commands.Range[int, 1, 999999999],
        unidade: str,
        prazo_iso: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        gid = await self.bot.db.create_goal(interaction.guild.id, titulo, alvo, unidade, prazo_iso)
        await interaction.response.send_message(f"Meta **#{gid}** criada.", ephemeral=True)

    @app_commands.command(name="metas_listar", description="Lista metas ativas recentes.")
    async def metas_listar(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_goals(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message("Sem metas.", ephemeral=True)
        lines = []
        for r in rows:
            lines.append(
                f"**#{r['id']}** {r['title']} — {r.get('current_value') or 0}/{r['target_value']} {r.get('unit')}"
            )
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="meta_progresso", description="Incrementa progresso de uma meta.")
    @staff_only()
    async def meta_progresso(
        self,
        interaction: discord.Interaction,
        id: int,
        delta: int,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.update_goal_progress(interaction.guild.id, id, delta)
        if not ok:
            return await interaction.response.send_message("Meta não encontrada.", ephemeral=True)
        await interaction.response.send_message(f"Progresso da meta **#{id}** atualizado (+{delta}).", ephemeral=True)

    @app_commands.command(name="meta_apagar", description="Remove uma meta pelo ID.")
    @staff_only()
    async def meta_apagar(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.delete_goal(interaction.guild.id, id)
        await interaction.response.send_message("Removida." if ok else "Não encontrada.", ephemeral=True)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Goals(bot))
