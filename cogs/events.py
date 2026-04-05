"""Eventos, RSVP e divulgação."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Events(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="evento_criar", description="Cria um evento do clube (datas em ISO UTC).")
    @staff_only()
    @app_commands.describe(
        titulo="Nome do evento",
        inicio_iso="Início: 2026-04-10T20:00:00+00:00",
        fim_iso="Fim opcional",
        descricao="Detalhes",
    )
    async def evento_criar(
        self,
        interaction: discord.Interaction,
        titulo: str,
        inicio_iso: str,
        fim_iso: str | None = None,
        descricao: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        eid = await self.bot.db.create_event(
            interaction.guild.id,
            titulo,
            inicio_iso,
            interaction.user.id,
            description=descricao,
            ends_at=fim_iso,
        )
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "evento_criar", {"id": eid})
        await interaction.response.send_message(f"Evento **#{eid}** criado: **{titulo}**", ephemeral=True)

    @app_commands.command(name="eventos_listar", description="Próximos eventos agendados.")
    async def eventos_listar(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_events(interaction.guild.id, 12)
        if not rows:
            return await interaction.response.send_message("Nenhum evento cadastrado.", ephemeral=True)
        lines = []
        for r in rows:
            lines.append(f"**#{r['id']}** — {r['title']}\n· Início `{r['starts_at']}`")
        embed = discord.Embed(title="Eventos", description="\n".join(lines), color=discord.Color.dark_magenta())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="evento_apagar", description="Remove um evento pelo ID.")
    @staff_only()
    async def evento_apagar(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.delete_event(interaction.guild.id, id)
        if not ok:
            return await interaction.response.send_message("Evento não encontrado.", ephemeral=True)
        await interaction.response.send_message(f"Evento **#{id}** removido.", ephemeral=True)

    @app_commands.command(name="evento_rsvp", description="Confirma presença em um evento.")
    @app_commands.describe(
        id="ID do evento (veja /eventos_listar)",
        status="confirmado | talvez | ausente",
    )
    async def evento_rsvp(self, interaction: discord.Interaction, id: int, status: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ev = await self.bot.db.get_event(interaction.guild.id, id)
        if not ev:
            return await interaction.response.send_message("Evento não encontrado neste servidor.", ephemeral=True)
        status_l = status.strip().lower()
        if status_l not in {"confirmado", "talvez", "ausente"}:
            return await interaction.response.send_message("Status inválido.", ephemeral=True)
        await self.bot.db.rsvp_set(id, interaction.user.id, status_l)
        await interaction.response.send_message(f"RSVP salvo: **{status_l}** no evento #{id}.", ephemeral=True)

    @app_commands.command(name="evento_participantes", description="Lista confirmações de um evento.")
    async def evento_participantes(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ev = await self.bot.db.get_event(interaction.guild.id, id)
        if not ev:
            return await interaction.response.send_message("Evento não encontrado.", ephemeral=True)
        rows = await self.bot.db.rsvp_list(id)
        if not rows:
            return await interaction.response.send_message("Nenhum RSVP ou evento sem registros.", ephemeral=True)
        by: dict[str, list[str]] = {"confirmado": [], "talvez": [], "ausente": []}
        for r in rows:
            by.setdefault(r["status"], []).append(f"<@{r['user_id']}>")
        desc = "\n".join(f"**{k}**: {', '.join(v) or '—'}" for k, v in by.items())
        await interaction.response.send_message(embed=discord.Embed(title=f"Evento #{id}", description=desc))

    @app_commands.command(name="evento_divulgar", description="Publica embed do evento no canal de eventos.")
    @staff_only()
    async def evento_divulgar(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_events(interaction.guild.id, 50)
        ev = next((r for r in rows if int(r["id"]) == id), None)
        if not ev:
            return await interaction.response.send_message("Evento não encontrado.", ephemeral=True)
        cfg = await self.bot.db.get_guild_config(interaction.guild.id)
        ch_id = cfg.get("event_channel_id")
        if not ch_id:
            return await interaction.response.send_message("Defina o canal com `/canal_eventos`.", ephemeral=True)
        ch = interaction.guild.get_channel(int(ch_id))
        if not isinstance(ch, discord.TextChannel):
            return await interaction.response.send_message("Canal inválido.", ephemeral=True)
        embed = discord.Embed(title=ev["title"], description=ev.get("description") or "", color=discord.Color.purple())
        embed.add_field(name="Início", value=str(ev["starts_at"]), inline=False)
        if ev.get("ends_at"):
            embed.add_field(name="Fim", value=str(ev["ends_at"]), inline=False)
        embed.set_footer(text=f"ID do evento: {id}")
        await ch.send(embed=embed)
        await interaction.response.send_message("Divulgado.", ephemeral=True)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Events(bot))
