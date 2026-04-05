"""Sistema de reputação / contribuição semanal e total."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Reputation(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="rep_adicionar", description="Soma pontos de reputação a um membro.")
    @staff_only()
    async def rep_adicionar(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        quantidade: app_commands.Range[int, 1, 500],
        motivo: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.upsert_member(interaction.guild.id, membro.id)
        row = await self.bot.db.add_rep(interaction.guild.id, membro.id, quantidade)
        await self.bot.db.audit(
            interaction.guild.id,
            interaction.user.id,
            "rep_adicionar",
            {"alvo": membro.id, "qtd": quantidade, "motivo": motivo},
        )
        cfg = await self.bot.db.get_guild_config(interaction.guild.id)
        msg = (
            f"{membro.mention} ganhou **+{quantidade}** REP. "
            f"Semana: **{row['rep_week']}** · Total: **{row['rep_total']}**"
        )
        if motivo:
            msg += f"\n_Motivo: {motivo}_"
        await interaction.response.send_message(msg, ephemeral=True)
        ch_id = cfg.get("rep_channel_id")
        if ch_id:
            ch = interaction.guild.get_channel(int(ch_id))
            if isinstance(ch, discord.TextChannel):
                await ch.send(msg[:2000])

    @app_commands.command(name="rep_remover", description="Remove pontos de reputação (mínimo 0).")
    @staff_only()
    async def rep_remover(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        quantidade: app_commands.Range[int, 1, 500],
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        row = await self.bot.db.subtract_rep(interaction.guild.id, membro.id, quantidade)
        if not row:
            return await interaction.response.send_message("Membro não cadastrado.", ephemeral=True)
        await self.bot.db.audit(
            interaction.guild.id,
            interaction.user.id,
            "rep_remover",
            {"alvo": membro.id, "qtd": quantidade},
        )
        await interaction.response.send_message(
            f"{membro.mention}: REP semana **{row['rep_week']}** · total **{row['rep_total']}**.",
            ephemeral=True,
        )

    @app_commands.command(name="rep_definir_semana", description="Define o valor absoluto da REP semanal.")
    @staff_only()
    async def rep_definir_semana(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        valor: app_commands.Range[int, 0, 999999],
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.upsert_member(interaction.guild.id, membro.id)
        await self.bot.db.set_rep_week(interaction.guild.id, membro.id, valor)
        await interaction.response.send_message(f"REP semanal de {membro.mention} definida em **{valor}**.", ephemeral=True)

    @app_commands.command(name="ranking_rep_semana", description="Top contribuições da semana.")
    @app_commands.describe(top="Quantos lugares exibir (máx. 15)")
    async def ranking_rep_semana(
        self,
        interaction: discord.Interaction,
        top: app_commands.Range[int, 3, 15] = 10,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.leaderboard(interaction.guild.id, "semana", top)
        lines = [f"{i}. <@{r['user_id']}> — **{r['rep_week']}**" for i, r in enumerate(rows, 1)]
        embed = discord.Embed(title="Ranking REP — semana", description="\n".join(lines) or "Vazio", color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ranking_rep_total", description="Top reputação acumulada.")
    async def ranking_rep_total(
        self,
        interaction: discord.Interaction,
        top: app_commands.Range[int, 3, 15] = 10,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.leaderboard(interaction.guild.id, "total", top)
        lines = [f"{i}. <@{r['user_id']}> — **{r['rep_total']}**" for i, r in enumerate(rows, 1)]
        embed = discord.Embed(title="Ranking REP — total", description="\n".join(lines) or "Vazio", color=discord.Color.dark_gold())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rep_reset_semana", description="Zera a REP semanal de todos os membros.")
    @staff_only()
    async def rep_reset_semana(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        n = await self.bot.db.reset_week_rep(interaction.guild.id)
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "rep_reset_semana", {"afetados": n})
        await interaction.response.send_message(f"Reset semanal aplicado. Linhas afetadas: **{n}**.", ephemeral=True)

    @app_commands.command(name="meu_rep", description="Mostra sua reputação semanal e total.")
    async def meu_rep(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        row = await self.bot.db.get_member(interaction.guild.id, interaction.user.id)
        if not row:
            return await interaction.response.send_message("Você ainda não está registrado.", ephemeral=True)
        await interaction.response.send_message(
            f"Semana: **{row.get('rep_week') or 0}** · Total: **{row.get('rep_total') or 0}**",
            ephemeral=True,
        )


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Reputation(bot))
