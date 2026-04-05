"""Verificações de permissão para interações do painel (views / modais)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot import Asphalt9Bot


def member_is_bot_owner(bot: Asphalt9Bot, user_id: int) -> bool:
    return user_id in bot.settings.owner_ids


def member_is_staff(member: discord.Member) -> bool:
    return bool(member.guild_permissions.manage_guild)


def member_is_admin(member: discord.Member) -> bool:
    return bool(member.guild_permissions.administrator)


async def reply_ephemeral(interaction: discord.Interaction, text: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)


async def ensure_guild(interaction: discord.Interaction) -> discord.Guild | None:
    if interaction.guild:
        return interaction.guild
    await reply_ephemeral(interaction, "Use isto dentro de um servidor.")
    return None


async def ensure_member(interaction: discord.Interaction) -> discord.Member | None:
    g = await ensure_guild(interaction)
    if not g:
        return None
    m = interaction.user
    if isinstance(m, discord.Member):
        return m
    fetched = g.get_member(interaction.user.id)
    if fetched:
        return fetched
    await reply_ephemeral(interaction, "Não foi possível resolver seu membro neste servidor.")
    return None


async def ensure_staff(interaction: discord.Interaction) -> discord.Member | None:
    m = await ensure_member(interaction)
    if not m:
        return None
    if member_is_staff(m):
        return m
    await reply_ephemeral(interaction, "Apenas **staff** (Gerenciar servidor) pode usar esta ação.")
    return None


async def ensure_admin(interaction: discord.Interaction) -> discord.Member | None:
    m = await ensure_member(interaction)
    if not m:
        return None
    if member_is_admin(m):
        return m
    await reply_ephemeral(interaction, "Apenas **administradores** podem usar esta ação.")
    return None


async def ensure_owner(interaction: discord.Interaction, bot: Asphalt9Bot) -> bool:
    if member_is_bot_owner(bot, interaction.user.id):
        return True
    await reply_ephemeral(interaction, "Apenas **donos do bot** podem usar esta ação.")
    return False
