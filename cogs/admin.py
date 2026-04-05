"""Comandos de administração do bot (dono) e utilidades avançadas."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import admin_only, is_bot_owner, staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Admin(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="admin_sync", description="Re-sincroniza comandos slash (dono do bot).")
    @is_bot_owner()
    async def admin_sync(self, interaction: discord.Interaction) -> None:
        guild = discord.Object(id=self.bot.settings.guild_id) if self.bot.settings.guild_id else None
        synced = await self.bot.tree.sync(guild=guild) if guild else await self.bot.tree.sync()
        await interaction.response.send_message(f"Sincronizado: **{len(synced)}** comandos.", ephemeral=True)

    @app_commands.command(name="admin_ping_db", description="Testa conexão com o banco (dono).")
    @is_bot_owner()
    async def admin_ping_db(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.get_guild_config(interaction.guild.id)
        await interaction.response.send_message("Banco respondendo.", ephemeral=True)

    @app_commands.command(name="admin_stats_memoria", description="Contagem aproximada de linhas em tabelas principais.")
    @is_bot_owner()
    async def admin_stats_memoria(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        counts = await self.bot.db.guild_row_counts(interaction.guild.id)
        await interaction.response.send_message(
            "Contagens: "
            + " · ".join(f"**{k}** {v}" for k, v in counts.items()),
            ephemeral=True,
        )

    @app_commands.command(name="staff_broadcast", description="Mensagem simples para o canal atual (staff).")
    @staff_only()
    async def staff_broadcast(self, interaction: discord.Interaction, mensagem: str) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Use em canal de texto.", ephemeral=True)
        await interaction.channel.send(mensagem[:2000])
        await interaction.response.send_message("Enviado.", ephemeral=True)

    @app_commands.command(name="staff_embed_rapido", description="Cria embed rápido com título e descrição.")
    @staff_only()
    async def staff_embed_rapido(
        self,
        interaction: discord.Interaction,
        titulo: str,
        descricao: str,
        cor: str = "3498db",
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Use em canal de texto.", ephemeral=True)
        try:
            c = int(cor.lstrip("#"), 16)
        except ValueError:
            c = 0x3498DB
        embed = discord.Embed(title=titulo, description=descricao, color=discord.Color(c))
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Embed publicado.", ephemeral=True)

    @app_commands.command(name="limpar_mensagens", description="Apaga até 50 mensagens recentes (precisa permissão no canal).")
    @admin_only()
    @app_commands.describe(quantidade="1 a 50")
    async def limpar_mensagens(
        self,
        interaction: discord.Interaction,
        quantidade: app_commands.Range[int, 1, 50],
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Use em canal de texto.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"Removidas **{len(deleted)}** mensagens.", ephemeral=True)

    @app_commands.command(name="staff_whois", description="Informações básicas de um usuário.")
    @staff_only()
    async def staff_whois(self, interaction: discord.Interaction, usuario: discord.User) -> None:
        embed = discord.Embed(title=str(usuario), color=discord.Color.light_gray())
        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.add_field(name="ID", value=str(usuario.id), inline=True)
        embed.add_field(name="Conta criada", value=str(usuario.created_at.date()), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="staff_role_members", description="Lista até 20 membros com um cargo.")
    @staff_only()
    async def staff_role_members(self, interaction: discord.Interaction, cargo: discord.Role) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        members = [m.mention for m in interaction.guild.members if cargo in m.roles][:20]
        await interaction.response.send_message(
            f"**{cargo.name}** ({len(members)} mostrados):\n" + ", ".join(members) if members else "Ninguém.",
            ephemeral=True,
        )


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Admin(bot))
