"""Verificações de permissão reutilizáveis para comandos slash."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

if TYPE_CHECKING:
    from bot import Asphalt9Bot


def is_bot_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        bot: Asphalt9Bot = interaction.client  # type: ignore[assignment]
        if interaction.user.id in bot.settings.owner_ids:
            return True
        await interaction.response.send_message(
            "Apenas donos do bot podem usar este comando.",
            ephemeral=True,
        )
        return False

    return app_commands.check(predicate)


def staff_only():
    """Líderes/staff: permissão Gerenciar Servidor no Discord."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return False
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        if member.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message(
            "Você precisa da permissão **Gerenciar servidor** para usar este comando.",
            ephemeral=True,
        )
        return False

    return app_commands.check(predicate)


def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return False
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        if member.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            "Você precisa ser **Administrador** para usar este comando.",
            ephemeral=True,
        )
        return False

    return app_commands.check(predicate)
