"""Engajamento: anúncios, lembretes, enquetes, papéis de escalação."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Engagement(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="anuncio_criar", description="Registra um anúncio oficial (histórico interno).")
    @staff_only()
    async def anuncio_criar(
        self,
        interaction: discord.Interaction,
        titulo: str,
        corpo: str,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        aid = await self.bot.db.create_announcement(interaction.guild.id, titulo, corpo, interaction.user.id)
        await interaction.response.send_message(f"Anúncio **#{aid}** salvo.", ephemeral=True)

    @app_commands.command(name="anuncios_recentes", description="Últimos anúncios registrados.")
    async def anuncios_recentes(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_announcements(interaction.guild.id, 6)
        if not rows:
            return await interaction.response.send_message("Sem anúncios.", ephemeral=True)
        embed = discord.Embed(title="Anúncios recentes", color=discord.Color.orange())
        for r in rows:
            embed.add_field(name=r["title"], value=(r["body"] or "")[:350], inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="anuncio_publicar", description="Publica o último anúncio no canal atual.")
    @staff_only()
    async def anuncio_publicar(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not interaction.channel:
            return await interaction.response.send_message("Use em um canal de texto.", ephemeral=True)
        rows = await self.bot.db.list_announcements(interaction.guild.id, 1)
        if not rows:
            return await interaction.response.send_message("Nenhum anúncio salvo.", ephemeral=True)
        r = rows[0]
        embed = discord.Embed(title=r["title"], description=r["body"], color=discord.Color.dark_orange())
        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Publicado.", ephemeral=True)

    @app_commands.command(name="lembrete", description="Agenda lembrete neste canal (minutos a partir de agora).")
    async def lembrete(
        self,
        interaction: discord.Interaction,
        minutos: app_commands.Range[int, 1, 10080],
        mensagem: str,
    ) -> None:
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Use em um canal de texto.", ephemeral=True)
        fire_at = (datetime.now(timezone.utc) + timedelta(minutes=minutos)).isoformat()
        rid = await self.bot.db.reminder_add(
            interaction.guild.id,
            interaction.channel.id,
            interaction.user.id,
            mensagem,
            fire_at,
        )
        await interaction.response.send_message(f"Lembrete **#{rid}** em ~{minutos} min.", ephemeral=True)

    @app_commands.command(name="lembretes_listar", description="Próximos lembretes agendados no servidor.")
    @staff_only()
    async def lembretes_listar(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.reminder_list_guild(interaction.guild.id, 20)
        if not rows:
            return await interaction.response.send_message("Nenhum lembrete.", ephemeral=True)
        lines = [f"**#{r['id']}** <#{r['channel_id']}> `{r['fire_at'][:19]}` — {r['message'][:80]}" for r in rows]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="lembrete_cancelar", description="Cancela lembrete pelo ID.")
    @staff_only()
    async def lembrete_cancelar(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.reminder_delete_for_guild(interaction.guild.id, id)
        await interaction.response.send_message("Cancelado." if ok else "ID não encontrado.", ephemeral=True)

    @app_commands.command(name="enquete_criar", description="Cria enquete com até 5 opções (separadas por | ).")
    @staff_only()
    @app_commands.describe(pergunta="Pergunta", opcoes="Ex.: Opção A | Opção B | Opção C")
    async def enquete_criar(self, interaction: discord.Interaction, pergunta: str, opcoes: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        parts = [p.strip() for p in opcoes.split("|") if p.strip()]
        if len(parts) < 2 or len(parts) > 5:
            return await interaction.response.send_message("Forneça entre 2 e 5 opções separadas por | .", ephemeral=True)
        pid = await self.bot.db.poll_create(interaction.guild.id, pergunta, parts, interaction.user.id)
        lines = "\n".join(f"{i}. {o}" for i, o in enumerate(parts))
        embed = discord.Embed(title=f"Enquete #{pid}", description=f"**{pergunta}**\n\n{lines}", color=discord.Color.blurple())
        embed.set_footer(text="Vote com /enquete_votar")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="enquete_votar", description="Registra seu voto em uma enquete aberta.")
    async def enquete_votar(
        self,
        interaction: discord.Interaction,
        id: int,
        opcao: app_commands.Range[int, 0, 4],
    ) -> None:
        poll = await self.bot.db.poll_get(id)
        if not poll or poll.get("closed"):
            return await interaction.response.send_message("Enquete inválida ou encerrada.", ephemeral=True)
        opts = json.loads(poll["options_json"])
        if opcao >= len(opts):
            return await interaction.response.send_message("Índice de opção inválido.", ephemeral=True)
        await self.bot.db.poll_vote(id, interaction.user.id, opcao)
        await interaction.response.send_message(f"Voto registrado: **{opts[opcao]}**", ephemeral=True)

    @app_commands.command(name="enquete_resultado", description="Mostra contagem de votos.")
    async def enquete_resultado(self, interaction: discord.Interaction, id: int) -> None:
        tally = await self.bot.db.poll_tally(id)
        if not tally:
            return await interaction.response.send_message("Enquete não encontrada.", ephemeral=True)
        opts = tally["options"]
        counts = tally["counts"]
        lines = []
        for i, o in enumerate(opts):
            lines.append(f"{i}. **{o}** — {counts.get(i, 0)} votos")
        status = "encerrada" if tally.get("closed") else "aberta"
        await interaction.response.send_message(f"Enquete #{id} ({status})\n" + "\n".join(lines))

    @app_commands.command(name="enquete_encerrar", description="Encerra enquete (congela votos).")
    @staff_only()
    async def enquete_encerrar(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.poll_close(interaction.guild.id, id)
        await interaction.response.send_message("Encerrada." if ok else "Não encontrada.", ephemeral=True)

    @app_commands.command(name="papel_escalacao_add", description="Define papéis táticos para escalação (texto).")
    @staff_only()
    async def papel_escalacao_add(
        self,
        interaction: discord.Interaction,
        nome: str,
        descricao: str | None,
        ordem: app_commands.Range[int, 0, 999] = 0,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.add_roster_role(interaction.guild.id, nome, descricao, ordem)
        await interaction.response.send_message(f"Papel **{nome}** salvo.", ephemeral=True)

    @app_commands.command(name="papeis_escalacao", description="Lista papéis de escalação cadastrados.")
    async def papeis_escalacao(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_roster_roles(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message("Nenhum papel cadastrado.", ephemeral=True)
        lines = [f"**{r['name']}** (ordem {r.get('sort_order')}) — {r.get('description') or '—'}" for r in rows[:20]]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="checkin", description="Marca atividade recente (atualiza last_active).")
    async def checkin(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.upsert_member(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message("Check-in registrado.", ephemeral=True)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Engagement(bot))
