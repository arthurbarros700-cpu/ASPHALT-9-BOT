"""Recrutamento e triagem de candidatos."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Recruitment(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="candidatar", description="Envia candidatura para entrar no clube.")
    @app_commands.describe(
        ign="Nick in-game",
        poder_garagem="Poder aproximado da garagem (número)",
        mensagem="Por que quer entrar / experiência em GP",
    )
    async def candidatar(
        self,
        interaction: discord.Interaction,
        ign: str,
        poder_garagem: app_commands.Range[int, 0, 999999] | None = None,
        mensagem: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        aid = await self.bot.db.create_application(
            interaction.guild.id,
            interaction.user.id,
            ign,
            poder_garagem,
            mensagem,
        )
        cfg = await self.bot.db.get_guild_config(interaction.guild.id)
        ch_id = cfg.get("recruit_channel_id")
        if ch_id:
            ch = interaction.guild.get_channel(int(ch_id))
            if isinstance(ch, discord.TextChannel):
                embed = discord.Embed(
                    title=f"Candidatura #{aid}",
                    color=discord.Color.green(),
                )
                embed.add_field(name="Usuário", value=interaction.user.mention, inline=False)
                embed.add_field(name="IGN", value=ign, inline=True)
                embed.add_field(name="Garagem", value=str(poder_garagem or "—"), inline=True)
                if mensagem:
                    embed.add_field(name="Mensagem", value=mensagem[:1000], inline=False)
                await ch.send(embed=embed)
        await interaction.response.send_message(f"Candidatura **#{aid}** enviada.", ephemeral=True)

    @app_commands.command(name="candidaturas_listar", description="Lista candidaturas recentes.")
    @staff_only()
    @app_commands.describe(status="aberta | aprovada | recusada (vazio = todas)")
    async def candidaturas_listar(self, interaction: discord.Interaction, status: str | None = None) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_applications(interaction.guild.id, status)
        if not rows:
            return await interaction.response.send_message("Nenhuma candidatura.", ephemeral=True)
        lines = []
        for r in rows[:12]:
            lines.append(
                f"**#{r['id']}** <@{r['user_id']}> — {r.get('ign') or '?'} — _{r.get('status')}_"
            )
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="candidatura_aprovar", description="Marca candidatura como aprovada.")
    @staff_only()
    async def candidatura_aprovar(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.review_application(interaction.guild.id, id, "aprovada", interaction.user.id)
        if not ok:
            return await interaction.response.send_message("ID inválido.", ephemeral=True)
        await interaction.response.send_message(f"Candidatura **#{id}** aprovada.", ephemeral=True)

    @app_commands.command(name="candidatura_recusar", description="Marca candidatura como recusada.")
    @staff_only()
    async def candidatura_recusar(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.review_application(interaction.guild.id, id, "recusada", interaction.user.id)
        if not ok:
            return await interaction.response.send_message("ID inválido.", ephemeral=True)
        await interaction.response.send_message(f"Candidatura **#{id}** recusada.", ephemeral=True)

    @app_commands.command(name="candidaturas_pendentes", description="Atalho para listar apenas abertas.")
    @staff_only()
    async def candidaturas_pendentes(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_applications(interaction.guild.id, "aberta")
        if not rows:
            return await interaction.response.send_message("Nenhuma pendente.", ephemeral=True)
        lines = [f"**#{r['id']}** <@{r['user_id']}> — {r.get('ign') or '?'}" for r in rows[:15]]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(
        name="modelo_recrutamento",
        description="Texto modelo para postar requisitos mínimos do clube.",
    )
    @staff_only()
    async def modelo_recrutamento(self, interaction: discord.Interaction) -> None:
        texto = (
            "**Requisitos exemplo (Asphalt 9)**\n"
            "· Atividade diária/semanal em eventos de clube\n"
            "· Participação em GP quando escalado\n"
            "· Discord obrigatório · respeito às regras internas\n"
            "· Envie `/candidatar` com IGN e poder da garagem\n"
        )
        await interaction.response.send_message(texto, ephemeral=True)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Recruitment(bot))
