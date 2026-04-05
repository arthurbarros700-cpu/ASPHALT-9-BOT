"""Comandos gerais: ajuda, latência, informações."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Meta(commands.Cog):
    """Utilitários e visão geral do bot."""

    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ajuda", description="Lista módulos e orientação de uso.")
    async def ajuda(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Asphalt 9 — Gestão de Clube",
            description=(
                "Bot profissional com **50+ comandos slash** organizados por área: "
                "**clube**, **membros**, **reputação**, **eventos**, **moderação**, "
                "**recrutamento**, **metas**, **garagem**, **engajamento**, **competitivo** e **admin**.\n\n"
                "Digite `/` e explore os comandos. Staff costuma precisar de **Gerenciar servidor** ou **Administrador**."
            ),
            color=discord.Color.dark_blue(),
        )
        embed.add_field(
            name="Primeiros passos",
            value=(
                "1. `/clube_nome` e `/clube_tag`\n"
                "2. `/canal_rep`, `/canal_eventos`, `/canal_recrutamento`\n"
                "3. Peça aos membros `/registrar`"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Mede latência WebSocket e API.")
    async def ping(self, interaction: discord.Interaction) -> None:
        ws = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! Latência WS: **{ws}** ms", ephemeral=True)

    @app_commands.command(name="sobre", description="Versão, stack e propósito do bot.")
    async def sobre(self, interaction: discord.Interaction) -> None:
        cmds = len([c for c in self.bot.tree.walk_commands() if isinstance(c, app_commands.Command)])
        embed = discord.Embed(
            title=self.bot.settings.bot_name,
            description="Gerenciamento de equipe para Asphalt 9 Legends no Discord.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Comandos slash", value=str(cmds), inline=True)
        embed.add_field(name="Persistência", value="SQLite (aiosqlite)", inline=True)
        embed.add_field(name="Biblioteca", value=f"discord.py {discord.__version__}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="convite_bot",
        description="Instruções para convidar o bot ao seu servidor (OAuth2).",
    )
    async def convite_bot(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "No Portal de Desenvolvedores do Discord, use **OAuth2 > URL Generator**: "
            "escopos `bot` + `applications.commands` e permissões mínimas: "
            "`Ver canais`, `Enviar mensagens`, `Incorporar links`, `Anexar arquivos`, "
            "`Ler histórico`, `Mencionar @everyone` (se usar anúncios), `Gerenciar eventos` (opcional).",
            ephemeral=True,
        )

    @app_commands.command(name="info_servidor", description="Estatísticas rápidas do servidor atual.")
    async def info_servidor(self, interaction: discord.Interaction) -> None:
        g = interaction.guild
        if not g:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        embed = discord.Embed(title=g.name, color=discord.Color.green())
        embed.add_field(name="Membros", value=str(g.member_count or 0), inline=True)
        embed.add_field(name="Canais", value=str(len(g.channels)), inline=True)
        embed.add_field(name="Cargos", value=str(len(g.roles)), inline=True)
        embed.set_thumbnail(url=g.icon.url if g.icon else discord.Embed.Empty)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats_bot", description="Uso aproximado: guilds e comandos registrados.")
    async def stats_bot(self, interaction: discord.Interaction) -> None:
        cmds = len([c for c in self.bot.tree.walk_commands() if isinstance(c, app_commands.Command)])
        await interaction.response.send_message(
            f"Servidores: **{len(self.bot.guilds)}** · Comandos slash: **{cmds}**",
            ephemeral=True,
        )


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Meta(bot))
