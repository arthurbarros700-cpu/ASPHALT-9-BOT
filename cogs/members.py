"""Cadastro e perfil de membros da equipe."""

from __future__ import annotations

import json
from io import BytesIO
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import admin_only, staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Members(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="registrar", description="Registra você no sistema do clube.")
    @app_commands.describe(ign="Seu nick in-game Asphalt 9")
    async def registrar(self, interaction: discord.Interaction, ign: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.upsert_member(interaction.guild.id, interaction.user.id, nickname=ign)
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "registrar", {"ign": ign})
        await interaction.response.send_message(f"Registrado como **{ign}**.", ephemeral=True)

    @app_commands.command(name="perfil", description="Mostra ficha do membro (REP, cargo interno, notas).")
    @app_commands.describe(membro="Membro a consultar (padrão: você)")
    async def perfil(self, interaction: discord.Interaction, membro: discord.Member | None = None) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        m = membro or interaction.user
        if not isinstance(m, discord.Member):
            return await interaction.response.send_message("Membro inválido.", ephemeral=True)
        row = await self.bot.db.get_member(interaction.guild.id, m.id)
        if not row:
            return await interaction.response.send_message("Membro ainda não registrado. Use `/registrar`.", ephemeral=True)
        embed = discord.Embed(title=f"Perfil — {m.display_name}", color=m.color if m.color.value else discord.Color.blurple())
        embed.add_field(name="IGN (bot)", value=row.get("nickname") or "—", inline=True)
        embed.add_field(name="Cargo interno", value=row.get("role") or "—", inline=True)
        embed.add_field(name="REP semana", value=str(row.get("rep_week") or 0), inline=True)
        embed.add_field(name="REP total", value=str(row.get("rep_total") or 0), inline=True)
        embed.add_field(name="Notas staff", value=(row.get("notes") or "—")[:900], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="listar_membros", description="Lista membros cadastrados ordenados por REP total.")
    @app_commands.describe(limite="Máximo 50")
    async def listar_membros(self, interaction: discord.Interaction, limite: app_commands.Range[int, 1, 50] = 20) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_members(interaction.guild.id, limite)
        if not rows:
            return await interaction.response.send_message("Nenhum membro cadastrado.", ephemeral=True)
        lines = []
        for i, r in enumerate(rows, 1):
            uid = int(r["user_id"])
            lines.append(f"{i}. <@{uid}> — **{r.get('nickname') or '?'}** · REP {r.get('rep_total') or 0}")
        embed = discord.Embed(title="Membros cadastrados", description="\n".join(lines[:20]), color=discord.Color.teal())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cargo_interno", description="Define cargo textual interno (não é cargo do Discord).")
    @staff_only()
    async def cargo_interno(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        cargo: str,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.upsert_member(interaction.guild.id, membro.id)
        await self.bot.db.set_member_role_name(interaction.guild.id, membro.id, cargo)
        await self.bot.db.audit(
            interaction.guild.id,
            interaction.user.id,
            "cargo_interno",
            {"alvo": membro.id, "cargo": cargo},
        )
        await interaction.response.send_message(f"{membro.mention} agora é **{cargo}** (interno).", ephemeral=True)

    @app_commands.command(name="atualizar_ign", description="Atualiza o nick in-game salvo no bot.")
    async def atualizar_ign(self, interaction: discord.Interaction, novo_ign: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        old = await self.bot.db.get_member(interaction.guild.id, interaction.user.id)
        old_ign = old.get("nickname") if old else None
        await self.bot.db.upsert_member(interaction.guild.id, interaction.user.id, nickname=novo_ign)
        await self.bot.db.nick_log(
            interaction.guild.id,
            interaction.user.id,
            old_ign,
            novo_ign,
            interaction.user.id,
        )
        await interaction.response.send_message(f"IGN atualizado para **{novo_ign}**.", ephemeral=True)

    @app_commands.command(name="historico_ign", description="Histórico de alterações de IGN.")
    @app_commands.describe(membro="Padrão: você")
    async def historico_ign(self, interaction: discord.Interaction, membro: discord.Member | None = None) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        m = membro or interaction.user
        if not isinstance(m, discord.Member):
            return await interaction.response.send_message("Membro inválido.", ephemeral=True)
        rows = await self.bot.db.nick_history_list(interaction.guild.id, m.id, 8)
        if not rows:
            return await interaction.response.send_message("Sem histórico.", ephemeral=True)
        lines = [f"`{r['changed_at'][:19]}`: {r.get('old_ign') or '?'} → **{r['new_ign']}**" for r in rows]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="notas_staff", description="Notas internas visíveis apenas via /perfil (staff).")
    @staff_only()
    async def notas_staff(self, interaction: discord.Interaction, membro: discord.Member, texto: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.upsert_member(interaction.guild.id, membro.id)
        await self.bot.db.set_member_notes(interaction.guild.id, membro.id, texto)
        await interaction.response.send_message("Notas atualizadas.", ephemeral=True)

    @app_commands.command(name="excluir_cadastro", description="Remove o membro do banco de dados do bot.")
    @admin_only()
    async def excluir_cadastro(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.remove_member(interaction.guild.id, membro.id)
        await self.bot.db.audit(interaction.guild.id, interaction.user.id, "excluir_cadastro", {"alvo": membro.id})
        await interaction.response.send_message("Cadastro removido.", ephemeral=True)

    @app_commands.command(name="membro_buscar_ign", description="Busca membros cadastrados por trecho do IGN (staff).")
    @staff_only()
    async def membro_buscar_ign(self, interaction: discord.Interaction, trecho: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.list_members(interaction.guild.id, 200)
        t = trecho.casefold()
        hits = [r for r in rows if (r.get("nickname") or "").casefold().find(t) >= 0][:15]
        if not hits:
            return await interaction.response.send_message("Nenhum resultado.", ephemeral=True)
        lines = [f"<@{r['user_id']}> — **{r.get('nickname')}**" for r in hits]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="exportar_clube", description="Gera JSON com snapshot (membros, eventos, metas...).")
    @staff_only()
    async def exportar_clube(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        snap = await self.bot.db.export_snapshot(interaction.guild.id)
        raw = json.dumps(snap, ensure_ascii=False, indent=2).encode("utf-8")
        file = discord.File(BytesIO(raw), filename="clube_export.json")
        await interaction.response.send_message("Exportação pronta.", file=file, ephemeral=True)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Members(bot))
