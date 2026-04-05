"""Moderação: strikes, lista negra, auditoria."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import admin_only, staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Moderation(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="strike_adicionar", description="Registra um strike disciplinar.")
    @staff_only()
    async def strike_adicionar(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        motivo: str,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        sid = await self.bot.db.add_strike(interaction.guild.id, membro.id, motivo, interaction.user.id)
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "strike", {"alvo": membro.id, "id": sid})
        await interaction.response.send_message(f"Strike **#{sid}** registrado para {membro.mention}.", ephemeral=True)

    @app_commands.command(name="strikes_ver", description="Lista strikes de um membro.")
    @staff_only()
    async def strikes_ver(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_strikes(interaction.guild.id, membro.id)
        if not rows:
            return await interaction.response.send_message("Sem strikes.", ephemeral=True)
        lines = [f"**#{r['id']}** `{r['created_at'][:19]}` — {r['reason']}" for r in rows[:10]]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="strikes_limpar", description="Remove todos os strikes de um membro.")
    @admin_only()
    async def strikes_limpar(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        n = await self.bot.db.clear_strikes(interaction.guild.id, membro.id)
        await interaction.response.send_message(f"Removidos **{n}** strikes.", ephemeral=True)

    @app_commands.command(name="lista_negra_add", description="Adiciona usuário à lista negra interna do clube.")
    @admin_only()
    async def lista_negra_add(
        self,
        interaction: discord.Interaction,
        usuario: discord.User,
        motivo: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.blacklist_add(interaction.guild.id, usuario.id, motivo, interaction.user.id)
        await interaction.response.send_message(f"{usuario.mention} adicionado à lista negra.", ephemeral=True)

    @app_commands.command(name="lista_negra_remover", description="Remove usuário da lista negra.")
    @admin_only()
    async def lista_negra_remover(self, interaction: discord.Interaction, usuario: discord.User) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.blacklist_remove(interaction.guild.id, usuario.id)
        await interaction.response.send_message("Removido." if ok else "Não estava na lista.", ephemeral=True)

    @app_commands.command(name="lista_negra_ver", description="Mostra entradas recentes da lista negra.")
    @staff_only()
    async def lista_negra_ver(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.blacklist_list(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message("Lista vazia.", ephemeral=True)
        lines = [f"<@{r['user_id']}> — {r.get('reason') or 'sem motivo'}" for r in rows[:15]]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="auditoria", description="Últimas ações administrativas registradas pelo bot.")
    @staff_only()
    async def auditoria(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.audit_recent(interaction.guild.id, 12)
        if not rows:
            return await interaction.response.send_message("Sem registros.", ephemeral=True)
        lines = []
        for r in rows:
            lines.append(f"`{r['created_at'][:19]}` <@{r['actor_id']}> — **{r['action']}**")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Moderation(bot))
