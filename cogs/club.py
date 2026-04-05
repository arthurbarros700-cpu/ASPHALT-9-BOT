"""Configuração do clube e canais preferenciais."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Club(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="clube_config", description="Mostra configuração salva do clube.")
    async def clube_config(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        cfg = await self.bot.db.get_guild_config(interaction.guild.id)
        embed = discord.Embed(title="Configuração do clube", color=discord.Color.gold())
        embed.add_field(name="Nome", value=cfg.get("club_name") or "—", inline=True)
        embed.add_field(name="Tag", value=cfg.get("club_tag") or "—", inline=True)
        embed.add_field(name="Fuso", value=cfg.get("timezone") or "—", inline=True)
        embed.add_field(name="Canal REP", value=f"<#{cfg['rep_channel_id']}>" if cfg.get("rep_channel_id") else "—", inline=True)
        embed.add_field(name="Canal eventos", value=f"<#{cfg['event_channel_id']}>" if cfg.get("event_channel_id") else "—", inline=True)
        embed.add_field(
            name="Canal recrutamento",
            value=f"<#{cfg['recruit_channel_id']}>" if cfg.get("recruit_channel_id") else "—",
            inline=True,
        )
        rules = (cfg.get("rules_text") or "")[:900]
        embed.add_field(name="Regras (trecho)", value=rules or "—", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clube_nome", description="Define o nome oficial do clube.")
    @app_commands.describe(nome="Nome exibido em relatórios e embeds.")
    @staff_only()
    async def clube_nome(self, interaction: discord.Interaction, nome: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.set_club_identity(interaction.guild.id, nome, None)
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "clube_nome", {"nome": nome})
        await interaction.response.send_message(f"Nome do clube atualizado: **{nome}**", ephemeral=True)

    @app_commands.command(name="clube_tag", description="Define a tag/abreviação do clube.")
    @app_commands.describe(tag="Ex.: [BR] ou A9X")
    @staff_only()
    async def clube_tag(self, interaction: discord.Interaction, tag: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.set_club_identity(interaction.guild.id, None, tag)
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "clube_tag", {"tag": tag})
        await interaction.response.send_message(f"Tag atualizada: **{tag}**", ephemeral=True)

    @app_commands.command(name="clube_fuso", description="Fuso horário textual (referência para eventos).")
    @app_commands.describe(fuso="Ex.: America/Sao_Paulo, Europe/Lisbon")
    @staff_only()
    async def clube_fuso(self, interaction: discord.Interaction, fuso: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.set_guild_timezone(interaction.guild.id, fuso)
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "clube_fuso", {"fuso": fuso})
        await interaction.response.send_message(f"Fuso salvo: `{fuso}`", ephemeral=True)

    @app_commands.command(name="canal_rep", description="Canal padrão para avisos de reputação.")
    @staff_only()
    async def canal_rep(self, interaction: discord.Interaction, canal: discord.TextChannel) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.set_channel_prefs(interaction.guild.id, rep_channel_id=canal.id)
        await interaction.response.send_message(f"Canal de REP: {canal.mention}", ephemeral=True)

    @app_commands.command(name="canal_eventos", description="Canal padrão para lembretes de eventos.")
    @staff_only()
    async def canal_eventos(self, interaction: discord.Interaction, canal: discord.TextChannel) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.set_channel_prefs(interaction.guild.id, event_channel_id=canal.id)
        await interaction.response.send_message(f"Canal de eventos: {canal.mention}", ephemeral=True)

    @app_commands.command(name="canal_recrutamento", description="Canal para candidaturas e triagem.")
    @staff_only()
    async def canal_recrutamento(self, interaction: discord.Interaction, canal: discord.TextChannel) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.set_channel_prefs(interaction.guild.id, recruit_channel_id=canal.id)
        await interaction.response.send_message(f"Canal de recrutamento: {canal.mention}", ephemeral=True)

    @app_commands.command(name="clube_regras", description="Armazena texto de regras internas do clube.")
    @staff_only()
    async def clube_regras(self, interaction: discord.Interaction, texto: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.set_rules(interaction.guild.id, texto)
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "clube_regras", {"len": len(texto)})
        await interaction.response.send_message("Regras salvas.", ephemeral=True)

    @app_commands.command(name="clube_resumo", description="Resumo público do clube para novos membros.")
    async def clube_resumo(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        cfg = await self.bot.db.get_guild_config(interaction.guild.id)
        nome = cfg.get("club_name") or interaction.guild.name
        tag = cfg.get("club_tag") or ""
        title = f"{nome} {tag}".strip()
        embed = discord.Embed(title=title, description="Bem-vindo ao clube Asphalt 9!", color=discord.Color.red())
        if cfg.get("rules_text"):
            embed.add_field(name="Regras", value=(cfg["rules_text"][:1000]), inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Club(bot))
