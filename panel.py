"""Painel interativo Legião Espartan — 100 ações via selects e modais."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import TYPE_CHECKING

import discord
from discord import ui

from legion_actions import ALL_ACTIONS, CATEGORIES, LegionAction
from permissions import (
    ensure_admin,
    ensure_guild,
    ensure_member,
    ensure_owner,
    ensure_staff,
    member_is_bot_owner,
    reply_ephemeral,
)

if TYPE_CHECKING:
    from bot import Asphalt9Bot

log = logging.getLogger(__name__)

DISCLOUD_TIP = (
    "**Discloud:** envie o zip com `main.py`, `discloud.config`, `requirements.txt` e o código. "
    "Variáveis: `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `PANEL_CHANNEL_ID`, `BOT_OWNER_IDS`; "
    "opcional `PANEL_LOGO_URLS` (URLs separadas por vírgula para rotação). `RAM=512` em geral suficiente."
)


async def get_logo_urls(bot: Asphalt9Bot, guild_id: int) -> list[str]:
    if bot.settings.logo_frame_urls:
        return list(bot.settings.logo_frame_urls)
    _idx, raw = await bot.db.get_panel_logo_state(guild_id)
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(u) for u in data if u]
        except json.JSONDecodeError:
            pass
    return []


async def current_thumbnail_url(bot: Asphalt9Bot, guild_id: int) -> str | None:
    urls = await get_logo_urls(bot, guild_id)
    if not urls:
        return None
    idx, _ = await bot.db.get_panel_logo_state(guild_id)
    return urls[idx % len(urls)]


async def advance_logo_frame(bot: Asphalt9Bot, guild_id: int) -> str | None:
    urls = await get_logo_urls(bot, guild_id)
    if not urls:
        return None
    idx, _ = await bot.db.get_panel_logo_state(guild_id)
    idx = idx % len(urls)
    url = urls[idx]
    new_idx = (idx + 1) % len(urls)
    await bot.db.set_panel_logo_state(guild_id, new_idx, json.dumps(urls, ensure_ascii=False))
    return url


def panel_embed(bot: Asphalt9Bot, guild: discord.Guild, logo_url: str | None) -> discord.Embed:
    embed = discord.Embed(
        title=f"◆ {bot.settings.legion_name}",
        description=(
            "**Centro de comando** — escolha **área** e **ação**. Tudo por **menus e formulários** "
            "(interface unificada, sem comandos soltos).\n\n"
            "_Logo animado:_ vários frames em `PANEL_LOGO_URLS` alternam automaticamente neste painel."
        ),
        color=0x8B0000,
    )
    embed.set_footer(text="Legião Espartan × Asphalt 9 · 100 funções · selects abaixo")
    if logo_url:
        embed.set_thumbnail(url=logo_url)
    embed.add_field(name="Servidor", value=guild.name[:256], inline=True)
    embed.add_field(name="Operador", value="Painel persistente", inline=True)
    embed.add_field(name="Bot", value=bot.user.display_name[:80] if bot.user else bot.settings.bot_name, inline=True)
    return embed


def tier_allowed(action: LegionAction, member: discord.Member, bot: Asphalt9Bot) -> bool:
    if action.tier == "owner":
        return member_is_bot_owner(bot, member.id)
    if action.tier == "admin":
        return member.guild_permissions.administrator or member_is_bot_owner(bot, member.id)
    if action.tier == "staff":
        return (
            member.guild_permissions.manage_guild
            or member.guild_permissions.administrator
            or member_is_bot_owner(bot, member.id)
        )
    if action.tier == "member":
        return True
    return True


async def ensure_tier(interaction: discord.Interaction, bot: Asphalt9Bot, action: LegionAction) -> discord.Member | None:
    m = await ensure_member(interaction)
    if not m:
        return None
    if not tier_allowed(action, m, bot):
        await reply_ephemeral(interaction, "Sem permissão para esta ação.")
        return None
    return m


def _opt(s: str) -> str | None:
    s = s.strip()
    return s if s else None


def _parse_int(s: str, field: str) -> int:
    s = s.strip()
    if not s:
        raise ValueError(f"{field} é obrigatório.")
    try:
        return int(s)
    except ValueError as e:
        raise ValueError(f"{field} deve ser um número inteiro.") from e


def _opt_int(s: str) -> int | None:
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError as e:
        raise ValueError("Número inválido em campo opcional.") from e


class LegionFormModal(ui.Modal):
    def __init__(self, bot: Asphalt9Bot, action_id: str, title: str, fields: list[tuple[str, str, bool, int]]) -> None:
        super().__init__(title=title[:45])
        self.bot = bot
        self.action_id = action_id
        for i, (label, placeholder, long, max_len) in enumerate(fields):
            style = discord.TextStyle.paragraph if long else discord.TextStyle.short
            self.add_item(
                ui.TextInput(
                    label=label[:45],
                    placeholder=(placeholder or None)[:100] if placeholder else None,
                    style=style,
                    required=False,
                    max_length=max_len,
                    custom_id=f"legion_f{i}",
                )
            )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        values = {item.custom_id: str(item.value).strip() for item in self.children if isinstance(item, ui.TextInput)}
        await dispatch_modal(self.bot, interaction, self.action_id, values)


class CategorySelect(ui.Select):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot
        opts = [
            discord.SelectOption(label=title[:100], value=key, description="20 ações nesta área")
            for key, title, _ in CATEGORIES
        ]
        super().__init__(
            placeholder="1) Escolha a área…",
            min_values=1,
            max_values=1,
            options=opts,
            custom_id="legion:cat",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await reply_ephemeral(interaction, "Sem servidor.")
            return
        cat = self.values[0]
        view = LegionActionView(self.bot, cat)
        logo = await current_thumbnail_url(self.bot, interaction.guild.id)
        emb = panel_embed(self.bot, interaction.guild, logo)
        await interaction.response.edit_message(embed=emb, view=view)


class ActionSelect(ui.Select):
    def __init__(self, bot: Asphalt9Bot, category_key: str) -> None:
        self.bot = bot
        actions = next(a for k, _t, a in CATEGORIES if k == category_key)
        opts = [
            discord.SelectOption(label=act.label[:100], value=act.id, description=(act.description or "")[:100])
            for act in actions
        ]
        super().__init__(
            placeholder="2) Escolha a ação…",
            min_values=1,
            max_values=1,
            options=opts,
            custom_id=f"legion:act:{category_key}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        act = ALL_ACTIONS[self.values[0]]
        await run_action(self.bot, interaction, act)


class BackButton(ui.Button):
    def __init__(self, bot: Asphalt9Bot, category_key: str) -> None:
        super().__init__(
            label="« Voltar",
            style=discord.ButtonStyle.secondary,
            custom_id=f"legion:back:{category_key}",
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.edit_message(view=LegionHomeView(self.bot))
            return
        view = LegionHomeView(self.bot)
        logo = await current_thumbnail_url(self.bot, interaction.guild.id)
        emb = panel_embed(self.bot, interaction.guild, logo)
        await interaction.response.edit_message(embed=emb, view=view)


class LegionHomeView(ui.View):
    def __init__(self, bot: Asphalt9Bot) -> None:
        super().__init__(timeout=None)
        self.add_item(CategorySelect(bot))


class LegionActionView(ui.View):
    def __init__(self, bot: Asphalt9Bot, category_key: str) -> None:
        super().__init__(timeout=None)
        self.add_item(ActionSelect(bot, category_key))
        self.add_item(BackButton(bot, category_key))


def register_panel_views(bot: Asphalt9Bot) -> None:
    bot.add_view(LegionHomeView(bot))
    for key, _title, _actions in CATEGORIES:
        bot.add_view(LegionActionView(bot, key))


async def refresh_panel_message(bot: Asphalt9Bot, guild: discord.Guild) -> None:
    mid = await bot.db.get_panel_message_id(guild.id)
    if not mid:
        return
    ch_id = bot.settings.panel_channel_id
    if not ch_id:
        return
    ch = guild.get_channel(ch_id)
    if not isinstance(ch, discord.TextChannel):
        return
    try:
        msg = await ch.fetch_message(mid)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return
    logo = await advance_logo_frame(bot, guild.id)
    if logo is None:
        logo = await current_thumbnail_url(bot, guild.id)
    await msg.edit(embed=panel_embed(bot, guild, logo), view=LegionHomeView(bot))


async def install_panel(bot: Asphalt9Bot, guild: discord.Guild) -> None:
    ch_id = bot.settings.panel_channel_id
    if not ch_id:
        log.warning("PANEL_CHANNEL_ID não definido; painel não instalado.")
        return
    ch = guild.get_channel(ch_id)
    if not isinstance(ch, discord.TextChannel):
        log.warning("Canal do painel inválido ou sem acesso.")
        return
    if bot.settings.logo_frame_urls:
        await bot.db.set_panel_logo_state(
            guild.id,
            0,
            json.dumps(list(bot.settings.logo_frame_urls), ensure_ascii=False),
        )
    logo = await advance_logo_frame(bot, guild.id)
    if logo is None:
        logo = await current_thumbnail_url(bot, guild.id)
    emb = panel_embed(bot, guild, logo)
    old_id = await bot.db.get_panel_message_id(guild.id)
    if old_id:
        try:
            old = await ch.fetch_message(old_id)
            await old.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
    msg = await ch.send(embed=emb, view=LegionHomeView(bot))
    await bot.db.set_panel_message(guild.id, msg.id)


async def run_action(bot: Asphalt9Bot, interaction: discord.Interaction, act: LegionAction) -> None:
    m = await ensure_tier(interaction, bot, act)
    if not m:
        return
    gid = interaction.guild.id if interaction.guild else 0

    # —— Modais por ID (gerado) ——
    modal_map: dict[str, tuple[str, list[tuple[str, str, bool, int]]]] = {
        "c02": ("Nome do clube", [("Nome", "", False, 80)]),
        "c03": ("Tag do clube", [("Tag", "ex: [SPN]", False, 16)]),
        "c04": ("Fuso horário", [("Fuso", "America/Sao_Paulo", False, 64)]),
        "c05": ("Canal REP", [("ID do canal", "", False, 22)]),
        "c06": ("Canal eventos", [("ID do canal", "", False, 22)]),
        "c07": ("Canal recrutamento", [("ID do canal", "", False, 22)]),
        "c08": ("Regras", [("Texto completo", "", True, 3900)]),
        "c13": ("Adicionar REP", [("ID usuário", "", False, 22), ("Quantidade", "1-500", False, 5), ("Motivo", "opcional", True, 500)]),
        "c14": ("Remover REP", [("ID usuário", "", False, 22), ("Quantidade", "", False, 5)]),
        "c15": ("REP semanal", [("ID usuário", "", False, 22), ("Valor", "", False, 8)]),
        "m01": ("Registrar", [("IGN in-game", "", False, 64)]),
        "m03": ("Perfil por ID", [("ID Discord", "", False, 22)]),
        "m05": ("Cargo interno", [("ID membro", "", False, 22), ("Cargo texto", "", False, 64)]),
        "m06": ("Novo IGN", [("IGN", "", False, 64)]),
        "m08": ("Histórico IGN", [("ID membro", "", False, 22)]),
        "m09": ("Notas staff", [("ID membro", "", False, 22), ("Notas", "", True, 1500)]),
        "m10": ("Excluir cadastro", [("ID membro", "", False, 22)]),
        "m11": ("Buscar IGN", [("Trecho", "", False, 40)]),
        "m14": ("Garagem", [("ID membro", "", False, 22)]),
        "m15": ("Campo garagem", [("Chave", "ex: carro_favorito", False, 40), ("Valor", "", True, 500)]),
        "m16": ("Poder garagem", [("Número", "", False, 10)]),
        "m17": ("Remover campo", [("Chave", "", False, 40)]),
        "m18": ("Template carro", [("Nome", "", False, 80), ("Estrelas 0-6", "", False, 2), ("Classe D-S", "D", False, 2)]),
        "m20": ("Whois", [("ID usuário", "", False, 22)]),
        "e01": ("Novo evento", [("Título", "", False, 120), ("Início ISO", "", False, 40), ("Fim ISO", "opcional", False, 40), ("Descrição", "opcional", True, 1500)]),
        "e03": ("Apagar evento", [("ID evento", "", False, 10)]),
        "e04": ("RSVP", [("ID evento", "", False, 10), ("Status", "confirmado|talvez|ausente", False, 12)]),
        "e05": ("Participantes", [("ID evento", "", False, 10)]),
        "e06": ("Divulgar", [("ID evento", "", False, 10)]),
        "e07": ("Anúncio", [("Título", "", False, 120), ("Corpo", "", True, 3500)]),
        "e10": ("Lembrete", [("Minutos", "1-10080", False, 6), ("Mensagem", "", True, 1500)]),
        "e12": ("Cancelar lembrete", [("ID lembrete", "", False, 10)]),
        "e13": ("Enquete", [("Pergunta", "", False, 200), ("Opções", "A | B | C", True, 500)]),
        "e14": ("Votar", [("ID enquete", "", False, 10), ("Índice opção", "0-4", False, 2)]),
        "e15": ("Resultado", [("ID enquete", "", False, 10)]),
        "e16": ("Encerrar enquete", [("ID enquete", "", False, 10)]),
        "e17": ("Papel escalação", [("Nome", "", False, 80), ("Ordem", "0-999", False, 4), ("Descrição", "opcional", True, 300)]),
        "e19": ("Broadcast", [("Mensagem", "", True, 2000)]),
        "e20": ("Embed", [("Título", "", False, 200), ("Descrição", "", True, 3500), ("Cor hex", "3498db", False, 8)]),
        "s01": ("Strike", [("ID membro", "", False, 22), ("Motivo", "", True, 500)]),
        "s02": ("Ver strikes", [("ID membro", "", False, 22)]),
        "s03": ("Limpar strikes", [("ID membro", "", False, 22)]),
        "s04": ("Lista negra +", [("ID usuário", "", False, 22), ("Motivo", "opcional", True, 300)]),
        "s05": ("Lista negra −", [("ID usuário", "", False, 22)]),
        "s08": ("Candidatura", [("IGN", "", False, 64), ("Poder garagem", "opcional", False, 8), ("Mensagem", "opcional", True, 1500)]),
        "s09": ("Candidaturas", [("Status", "vazio|aberta|aprovada|recusada", False, 12)]),
        "s10": ("Aprovar", [("ID candidatura", "", False, 10)]),
        "s11": ("Recusar", [("ID candidatura", "", False, 10)]),
        "s14": ("Meta", [("Título", "", False, 120), ("Alvo numérico", "", False, 12), ("Unidade", "rep", False, 32), ("Prazo ISO", "opcional", False, 40)]),
        "s16": ("Progresso meta", [("ID meta", "", False, 10), ("Delta", "+/-", False, 10)]),
        "s17": ("Apagar meta", [("ID meta", "", False, 10)]),
        "s18": ("Limpar msgs", [("Quantidade 1-50", "", False, 3)]),
        "s19": ("Cargo Discord", [("ID do cargo", "", False, 22)]),
        "k01": ("Guerra", [("Adversário", "", False, 80), ("Resultado", "vitória|derrota|empate", False, 12), ("Data ISO", "", False, 40), ("Nosso placar", "opcional", False, 4), ("Placar adv", "opcional", False, 4), ("Notas", "opcional", True, 500)]),
        "k03": ("Treino", [("Tema", "", False, 120), ("Quando ISO", "", False, 40), ("ID coach", "opcional", False, 22), ("Notas", "opcional", True, 500)]),
        "k05": ("Patrocínio", [("Parceiro", "", False, 120), ("Valor texto", "opcional", False, 80), ("Início ISO", "opcional", False, 40), ("Fim ISO", "opcional", False, 40), ("Notas", "opcional", True, 500)]),
        "k07": ("Tarefa", [("Título", "", False, 200), ("ID responsável", "opcional", False, 22), ("Prazo ISO", "opcional", False, 40)]),
        "k08": ("Listar tarefas", [("Status", "vazio ou aberta/feita", False, 20)]),
        "k09": ("Status tarefa", [("ID tarefa", "", False, 10), ("Novo status", "", False, 32)]),
    }

    if act.id in modal_map:
        title, fields = modal_map[act.id]
        await interaction.response.send_modal(LegionFormModal(bot, act.id, title, fields))
        return

    # —— Ações imediatas ——
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await execute_immediate(bot, interaction, act, m, gid)
    except Exception:
        log.exception("execute_immediate %s", act.id)
        await interaction.followup.send("Erro ao executar a ação.", ephemeral=True)


async def execute_immediate(
    bot: Asphalt9Bot,
    interaction: discord.Interaction,
    act: LegionAction,
    member: discord.Member,
    gid: int,
) -> None:
    aid = act.id

    if aid == "c01":
        cfg = await bot.db.get_guild_config(gid)
        lines = [
            f"**Nome:** {cfg.get('club_name') or '—'}",
            f"**Tag:** {cfg.get('club_tag') or '—'}",
            f"**Fuso:** {cfg.get('timezone') or '—'}",
            f"**Canal REP:** {cfg.get('rep_channel_id') or '—'}",
            f"**Eventos:** {cfg.get('event_channel_id') or '—'}",
            f"**Recrutamento:** {cfg.get('recruit_channel_id') or '—'}",
        ]
        await interaction.followup.send("\n".join(lines), ephemeral=True)
        return

    if aid == "c09":
        cfg = await bot.db.get_guild_config(gid)
        nome = cfg.get("club_name") or interaction.guild.name
        tag = cfg.get("club_tag") or ""
        emb = discord.Embed(title=f"{nome} {tag}".strip(), color=0xC0392B)
        if cfg.get("rules_text"):
            emb.description = str(cfg["rules_text"])[:4000]
        await interaction.followup.send(embed=emb, ephemeral=False)
        return

    if aid == "c11":
        rows = await bot.db.leaderboard(gid, "semana", 10)
        lines = [f"{i}. <@{r['user_id']}> — **{r['rep_week']}**" for i, r in enumerate(rows, 1)]
        await interaction.followup.send("**Ranking semana**\n" + ("\n".join(lines) or "Vazio"), ephemeral=True)
        return

    if aid == "c12":
        rows = await bot.db.leaderboard(gid, "total", 10)
        lines = [f"{i}. <@{r['user_id']}> — **{r['rep_total']}**" for i, r in enumerate(rows, 1)]
        await interaction.followup.send("**Ranking total**\n" + ("\n".join(lines) or "Vazio"), ephemeral=True)
        return

    if aid == "c16":
        if not await ensure_staff(interaction):
            return
        n = await bot.db.reset_week_rep(gid)
        await bot.db.audit(gid, member.id, "rep_reset_semana", {"n": n})
        await interaction.followup.send(f"Reset semanal: **{n}** linhas.", ephemeral=True)
        return

    if aid == "c17":
        await interaction.followup.send(
            "Use datas **ISO 8601** com fuso, ex.: `2026-04-10T20:00:00-03:00`.",
            ephemeral=True,
        )
        return

    if aid == "c18":
        await interaction.followup.send(
            "**Briefing GP:** mapa, papéis, comunicação, plano B.",
            ephemeral=True,
        )
        return

    if aid == "c19":
        if not await ensure_staff(interaction):
            return
        snap = await bot.db.export_snapshot(gid)
        raw = json.dumps(snap, ensure_ascii=False, indent=2).encode("utf-8")
        await interaction.followup.send(
            file=discord.File(BytesIO(raw), filename="legion_export.json"),
            ephemeral=True,
        )
        return

    if aid == "c20":
        ws = round(bot.latency * 1000)
        await interaction.followup.send(f"Latência WS: **{ws}** ms", ephemeral=True)
        return

    if aid == "c10":
        row = await bot.db.get_member(gid, member.id)
        if not row:
            await interaction.followup.send("Registre-se primeiro (ação **Registrar-me**).", ephemeral=True)
            return
        await interaction.followup.send(
            f"Semana: **{row.get('rep_week') or 0}** · Total: **{row.get('rep_total') or 0}**",
            ephemeral=True,
        )
        return

    if aid == "m02":
        row = await bot.db.get_member(gid, member.id)
        if not row:
            await interaction.followup.send("Não registrado.", ephemeral=True)
            return
        emb = discord.Embed(title=f"Perfil — {member.display_name}", color=member.color if member.color.value else 0x5865F2)
        emb.add_field(name="IGN", value=row.get("nickname") or "—", inline=True)
        emb.add_field(name="Cargo interno", value=row.get("role") or "—", inline=True)
        emb.add_field(name="REP", value=f"{row.get('rep_week') or 0} / {row.get('rep_total') or 0}", inline=False)
        await interaction.followup.send(embed=emb, ephemeral=True)
        return

    if aid == "m04":
        rows = await bot.db.list_members(gid, 25)
        lines = [f"{i}. <@{r['user_id']}> — {r.get('nickname') or '?'} · {r.get('rep_total') or 0}" for i, r in enumerate(rows, 1)]
        await interaction.followup.send("\n".join(lines) or "Vazio", ephemeral=True)
        return

    if aid == "m07":
        rows = await bot.db.nick_history_list(gid, member.id, 8)
        if not rows:
            await interaction.followup.send("Sem histórico.", ephemeral=True)
            return
        lines = [f"`{r['changed_at'][:19]}` {r.get('old_ign') or '?'} → **{r['new_ign']}**" for r in rows]
        await interaction.followup.send("\n".join(lines), ephemeral=True)
        return

    if aid == "m12":
        await bot.db.upsert_member(gid, member.id)
        await interaction.followup.send("Check-in OK.", ephemeral=True)
        return

    if aid == "m13":
        g = await bot.db.garage_get(gid, member.id)
        await interaction.followup.send(f"```json\n{json.dumps(g, ensure_ascii=False)[:1800]}\n```", ephemeral=True)
        return

    if aid == "m19":
        rows = await bot.db.car_templates_list(gid)
        lines = [f"**{r['name']}** {r.get('stars')}★ {r.get('car_class')}" for r in rows[:20]]
        await interaction.followup.send("\n".join(lines) or "Vazio", ephemeral=True)
        return

    if aid == "e02":
        rows = await bot.db.list_events(gid, 15)
        lines = [f"**#{r['id']}** {r['title']} — `{r['starts_at']}`" for r in rows]
        await interaction.followup.send("\n".join(lines) or "Nenhum evento.", ephemeral=True)
        return

    if aid == "e08":
        rows = await bot.db.list_announcements(gid, 6)
        if not rows:
            await interaction.followup.send("Sem anúncios.", ephemeral=True)
            return
        emb = discord.Embed(title="Anúncios", color=0xE67E22)
        for r in rows:
            emb.add_field(name=r["title"][:256], value=(r["body"] or "")[:350], inline=False)
        await interaction.followup.send(embed=emb, ephemeral=True)
        return

    if aid == "e09":
        if not await ensure_staff(interaction):
            return
        rows = await bot.db.list_announcements(gid, 1)
        if not rows:
            await interaction.followup.send("Sem anúncios salvos.", ephemeral=True)
            return
        r = rows[0]
        pch = bot.settings.panel_channel_id
        if not pch or not interaction.guild:
            await interaction.followup.send("PANEL_CHANNEL_ID não configurado.", ephemeral=True)
            return
        ch = interaction.guild.get_channel(pch)
        if not isinstance(ch, discord.TextChannel):
            await interaction.followup.send("Canal do painel inválido.", ephemeral=True)
            return
        emb = discord.Embed(title=r["title"], description=r["body"], color=0xD35400)
        await ch.send(embed=emb)
        await interaction.followup.send("Último anúncio publicado no canal do painel.", ephemeral=True)
        return

    if aid == "e11":
        if not await ensure_staff(interaction):
            return
        rows = await bot.db.reminder_list_guild(gid, 20)
        lines = [f"**#{r['id']}** <#{r['channel_id']}> `{r['fire_at'][:19]}`" for r in rows]
        await interaction.followup.send("\n".join(lines) or "Nenhum.", ephemeral=True)
        return

    if aid == "e18":
        rows = await bot.db.list_roster_roles(gid)
        lines = [f"**{r['name']}** ({r.get('sort_order')}) — {r.get('description') or '—'}" for r in rows[:20]]
        await interaction.followup.send("\n".join(lines) or "Vazio", ephemeral=True)
        return

    if aid == "s06":
        if not await ensure_staff(interaction):
            return
        rows = await bot.db.blacklist_list(gid)
        lines = [f"<@{r['user_id']}> — {r.get('reason') or '—'}" for r in rows[:15]]
        await interaction.followup.send("\n".join(lines) or "Lista vazia.", ephemeral=True)
        return

    if aid == "s07":
        if not await ensure_staff(interaction):
            return
        rows = await bot.db.audit_recent(gid, 12)
        lines = [f"`{r['created_at'][:19]}` <@{r['actor_id']}> **{r['action']}**" for r in rows]
        await interaction.followup.send("\n".join(lines) or "Vazio.", ephemeral=True)
        return

    if aid == "s12":
        if not await ensure_staff(interaction):
            return
        rows = await bot.db.list_applications(gid, "aberta")
        lines = [f"**#{r['id']}** <@{r['user_id']}> — {r.get('ign') or '?'}" for r in rows[:15]]
        await interaction.followup.send("\n".join(lines) or "Nenhuma.", ephemeral=True)
        return

    if aid == "s13":
        await interaction.followup.send(
            "**Requisitos exemplo:** atividade, GP, Discord, respeito às regras. Candidatura pelo painel.",
            ephemeral=True,
        )
        return

    if aid == "s15":
        rows = await bot.db.list_goals(gid)
        lines = [f"**#{r['id']}** {r['title']} — {r.get('current_value') or 0}/{r['target_value']} {r.get('unit')}" for r in rows]
        await interaction.followup.send("\n".join(lines) or "Sem metas.", ephemeral=True)
        return

    if aid == "s20":
        g = interaction.guild
        emb = discord.Embed(title=g.name, color=0x2ECC71)
        emb.add_field(name="Membros", value=str(g.member_count or 0), inline=True)
        emb.add_field(name="Canais", value=str(len(g.channels)), inline=True)
        await interaction.followup.send(embed=emb, ephemeral=True)
        return

    if aid == "k02":
        rows = await bot.db.war_list(gid, 12)
        lines = []
        for r in rows:
            sc = ""
            if r.get("score_us") is not None and r.get("score_them") is not None:
                sc = f" ({r['score_us']}x{r['score_them']})"
            lines.append(f"`{str(r['war_date'])[:10]}` vs **{r['opponent']}** — {r['result']}{sc}")
        await interaction.followup.send("\n".join(lines) or "Sem guerras.", ephemeral=True)
        return

    if aid == "k04":
        rows = await bot.db.training_list(gid, 12)
        lines = [f"**#{r['id']}** {r['topic']} — `{r['scheduled_at']}`" for r in rows]
        await interaction.followup.send("\n".join(lines) or "Sem treinos.", ephemeral=True)
        return

    if aid == "k06":
        rows = await bot.db.sponsor_list(gid, 10)
        lines = [f"**{r['partner']}** — {r.get('value_text') or '—'}" for r in rows]
        await interaction.followup.send("\n".join(lines) or "Vazio.", ephemeral=True)
        return

    if aid == "k10":
        emb = discord.Embed(
            title=bot.settings.bot_name,
            description="Painel Legião Espartan · SQLite · discord.py",
            color=0x1ABC9C,
        )
        emb.add_field(name="Funções", value="100 (via painel)", inline=True)
        await interaction.followup.send(embed=emb, ephemeral=True)
        return

    if aid == "k11":
        if not await ensure_staff(interaction):
            return
        if interaction.guild:
            await refresh_panel_message(bot, interaction.guild)
        await interaction.followup.send("Painel atualizado.", ephemeral=True)
        return

    if aid == "k12":
        if not await ensure_owner(interaction, bot):
            return
        if interaction.guild:
            await install_panel(bot, interaction.guild)
        await interaction.followup.send("Painel repostado.", ephemeral=True)
        return

    if aid == "k13":
        if not await ensure_owner(interaction, bot):
            return
        await bot.db.get_guild_config(gid)
        await interaction.followup.send("SQLite OK.", ephemeral=True)
        return

    if aid == "k14":
        if not await ensure_owner(interaction, bot):
            return
        c = await bot.db.guild_row_counts(gid)
        await interaction.followup.send(" · ".join(f"{k}: **{v}**" for k, v in c.items()), ephemeral=True)
        return

    if aid == "k15":
        chunk = ", ".join(sorted(ALL_ACTIONS.keys()))
        await interaction.followup.send(f"IDs: `{chunk[:1900]}`", ephemeral=True)
        return

    if aid == "k16":
        await interaction.followup.send(
            "OAuth2: escopos `bot` + `applications.commands`; permissões: ver canais, enviar mensagens, embeds, ler histórico.",
            ephemeral=True,
        )
        return

    if aid == "k17":
        if not await ensure_owner(interaction, bot):
            return
        await interaction.followup.send(DISCLOUD_TIP, ephemeral=True)
        return

    if aid == "k18":
        await interaction.followup.send(
            "**Legião Espartan** — disciplina, nitro na medida, vitória coletiva.",
            ephemeral=True,
        )
        return

    if aid == "k19":
        await interaction.followup.send(
            "**Defesa:** conserve nitro para ressalto; não gaste tudo na largada; memorize atalhos do mapa.",
            ephemeral=True,
        )
        return

    if aid == "k20":
        await interaction.followup.send(
            "Suporte: contate os **donos do bot** (IDs em `BOT_OWNER_IDS`).",
            ephemeral=True,
        )
        return

    await interaction.followup.send("Ação ainda não mapeada (reporte ao dev).", ephemeral=True)


async def dispatch_modal(bot: Asphalt9Bot, interaction: discord.Interaction, action_id: str, v: dict[str, str]) -> None:
    act = ALL_ACTIONS[action_id]
    m = await ensure_tier(interaction, bot, act)
    if not m:
        return
    gid = interaction.guild.id if interaction.guild else 0

    def gv(i: int) -> str:
        return v.get(f"legion_f{i}", "").strip()

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        if action_id == "c02":
            await bot.db.set_club_identity(gid, gv(0), None)
            await bot.db.audit(gid, m.id, "clube_nome", {"nome": gv(0)})
            await interaction.followup.send("Nome atualizado.", ephemeral=True)
        elif action_id == "c03":
            await bot.db.set_club_identity(gid, None, gv(0))
            await interaction.followup.send("Tag atualizada.", ephemeral=True)
        elif action_id == "c04":
            await bot.db.set_guild_timezone(gid, gv(0))
            await interaction.followup.send("Fuso salvo.", ephemeral=True)
        elif action_id == "c05":
            await bot.db.set_channel_prefs(gid, rep_channel_id=_parse_int(gv(0), "ID do canal"))
            await interaction.followup.send("Canal REP salvo.", ephemeral=True)
        elif action_id == "c06":
            await bot.db.set_channel_prefs(gid, event_channel_id=_parse_int(gv(0), "ID do canal"))
            await interaction.followup.send("Canal eventos salvo.", ephemeral=True)
        elif action_id == "c07":
            await bot.db.set_channel_prefs(gid, recruit_channel_id=_parse_int(gv(0), "ID do canal"))
            await interaction.followup.send("Canal recrutamento salvo.", ephemeral=True)
        elif action_id == "c08":
            await bot.db.set_rules(gid, gv(0))
            await interaction.followup.send("Regras salvas.", ephemeral=True)
        elif action_id == "c13":
            uid, q, reason = _parse_int(gv(0), "ID usuário"), _parse_int(gv(1), "Quantidade"), _opt(gv(2))
            await bot.db.upsert_member(gid, uid)
            row = await bot.db.add_rep(gid, uid, q)
            await bot.db.audit(gid, m.id, "rep_add", {"uid": uid, "q": q})
            msg = f"<@{uid}> +{q} REP → semana **{row['rep_week']}** total **{row['rep_total']}**"
            cfg = await bot.db.get_guild_config(gid)
            ch_id = cfg.get("rep_channel_id")
            if ch_id and interaction.guild:
                ch = interaction.guild.get_channel(int(ch_id))
                if isinstance(ch, discord.TextChannel):
                    await ch.send((msg + (f"\n_{reason}_" if reason else ""))[:2000])
            await interaction.followup.send("REP aplicada.", ephemeral=True)
        elif action_id == "c14":
            uid, q = _parse_int(gv(0), "ID usuário"), _parse_int(gv(1), "Quantidade")
            row = await bot.db.subtract_rep(gid, uid, q)
            await interaction.followup.send("Atualizado." if row else "Membro não encontrado.", ephemeral=True)
        elif action_id == "c15":
            uid = _parse_int(gv(0), "ID usuário")
            val = _parse_int(gv(1), "Valor")
            await bot.db.upsert_member(gid, uid)
            await bot.db.set_rep_week(gid, uid, val)
            await interaction.followup.send("REP semanal definida.", ephemeral=True)
        elif action_id == "m01":
            ign = gv(0)
            if not ign:
                await interaction.followup.send("IGN obrigatório.", ephemeral=True)
                return
            await bot.db.upsert_member(gid, m.id, nickname=ign)
            await interaction.followup.send(f"Registrado: **{ign}**", ephemeral=True)
        elif action_id == "m03":
            uid = _parse_int(gv(0), "ID Discord")
            row = await bot.db.get_member(gid, uid)
            if not row:
                await interaction.followup.send("Não encontrado.", ephemeral=True)
                return
            await interaction.followup.send(
                f"<@{uid}> IGN **{row.get('nickname') or '?'}** · REP {row.get('rep_week')}/{row.get('rep_total')}",
                ephemeral=True,
            )
        elif action_id == "m05":
            uid = _parse_int(gv(0), "ID membro")
            await bot.db.upsert_member(gid, uid)
            await bot.db.set_member_role_name(gid, uid, gv(1))
            await interaction.followup.send("Cargo interno OK.", ephemeral=True)
        elif action_id == "m06":
            old = await bot.db.get_member(gid, m.id)
            old_ign = old.get("nickname") if old else None
            await bot.db.upsert_member(gid, m.id, nickname=gv(0))
            await bot.db.nick_log(gid, m.id, old_ign, gv(0), m.id)
            await interaction.followup.send("IGN atualizado.", ephemeral=True)
        elif action_id == "m08":
            rows = await bot.db.nick_history_list(gid, _parse_int(gv(0), "ID membro"), 8)
            await interaction.followup.send("\n".join(f"{r['new_ign']}" for r in rows) or "Vazio.", ephemeral=True)
        elif action_id == "m09":
            uid = _parse_int(gv(0), "ID membro")
            await bot.db.upsert_member(gid, uid)
            await bot.db.set_member_notes(gid, uid, gv(1))
            await interaction.followup.send("Notas salvas.", ephemeral=True)
        elif action_id == "m10":
            await bot.db.remove_member(gid, _parse_int(gv(0), "ID membro"))
            await interaction.followup.send("Removido.", ephemeral=True)
        elif action_id == "m11":
            t = gv(0).casefold()
            rows = await bot.db.list_members(gid, 200)
            hits = [r for r in rows if (r.get("nickname") or "").casefold().find(t) >= 0][:12]
            await interaction.followup.send(
                "\n".join(f"<@{r['user_id']}> — {r.get('nickname')}" for r in hits) or "Nenhum.",
                ephemeral=True,
            )
        elif action_id == "m14":
            g = await bot.db.garage_get(gid, _parse_int(gv(0), "ID membro"))
            await interaction.followup.send(f"```json\n{json.dumps(g, ensure_ascii=False)[:1800]}\n```", ephemeral=True)
        elif action_id == "m15":
            await bot.db.upsert_member(gid, m.id)
            await bot.db.garage_set_field(gid, m.id, gv(0), gv(1))
            await interaction.followup.send("Campo salvo.", ephemeral=True)
        elif action_id == "m16":
            await bot.db.upsert_member(gid, m.id)
            await bot.db.garage_set_field(gid, m.id, "poder", _parse_int(gv(0), "Poder"))
            await interaction.followup.send("Poder salvo.", ephemeral=True)
        elif action_id == "m17":
            ok = await bot.db.garage_delete_field(gid, m.id, gv(0))
            await interaction.followup.send("Removido." if ok else "Não encontrado.", ephemeral=True)
        elif action_id == "m18":
            try:
                stars = int(gv(1).strip()) if gv(1).strip() else 0
            except ValueError:
                await interaction.followup.send("Estrelas deve ser um número 0–6.", ephemeral=True)
                return
            stars = max(0, min(6, stars))
            await bot.db.car_template_add(gid, gv(0), stars, (gv(2) or "D").upper()[:1])
            await interaction.followup.send("Template salvo.", ephemeral=True)
        elif action_id == "m20":
            u = await bot.fetch_user(_parse_int(gv(0), "ID usuário"))
            emb = discord.Embed(title=str(u))
            emb.set_thumbnail(url=u.display_avatar.url)
            emb.add_field(name="ID", value=str(u.id))
            await interaction.followup.send(embed=emb, ephemeral=True)
        elif action_id == "e01":
            eid = await bot.db.create_event(gid, gv(0), gv(1), m.id, description=_opt(gv(3)), ends_at=_opt(gv(2)))
            await interaction.followup.send(f"Evento **#{eid}** criado.", ephemeral=True)
        elif action_id == "e03":
            ok = await bot.db.delete_event(gid, _parse_int(gv(0), "ID evento"))
            await interaction.followup.send("Apagado." if ok else "Não encontrado.", ephemeral=True)
        elif action_id == "e04":
            st = gv(1).lower()
            if st not in {"confirmado", "talvez", "ausente"}:
                await interaction.followup.send("Status inválido.", ephemeral=True)
                return
            eid = _parse_int(gv(0), "ID evento")
            if not await bot.db.get_event(gid, eid):
                await interaction.followup.send("Evento inexistente.", ephemeral=True)
                return
            await bot.db.rsvp_set(eid, m.id, st)
            await interaction.followup.send("RSVP salvo.", ephemeral=True)
        elif action_id == "e05":
            rows = await bot.db.rsvp_list(_parse_int(gv(0), "ID evento"))
            by: dict[str, list[str]] = {}
            for r in rows:
                by.setdefault(r["status"], []).append(f"<@{r['user_id']}>")
            await interaction.followup.send(
                "\n".join(f"**{k}:** {', '.join(v)}" for k, v in by.items()) or "Sem RSVP.",
                ephemeral=True,
            )
        elif action_id == "e06":
            evs = await bot.db.list_events(gid, 80)
            eid = _parse_int(gv(0), "ID evento")
            ev = next((x for x in evs if int(x["id"]) == eid), None)
            if not ev:
                await interaction.followup.send("Evento não encontrado.", ephemeral=True)
                return
            cfg = await bot.db.get_guild_config(gid)
            ch_id = cfg.get("event_channel_id")
            if not ch_id or not interaction.guild:
                await interaction.followup.send("Canal de eventos não configurado.", ephemeral=True)
                return
            ch = interaction.guild.get_channel(int(ch_id))
            if not isinstance(ch, discord.TextChannel):
                await interaction.followup.send("Canal inválido.", ephemeral=True)
                return
            emb = discord.Embed(title=ev["title"], description=ev.get("description") or "")
            emb.add_field(name="Início", value=str(ev["starts_at"]))
            await ch.send(embed=emb)
            await interaction.followup.send("Divulgado.", ephemeral=True)
        elif action_id == "e07":
            aid = await bot.db.create_announcement(gid, gv(0), gv(1), m.id)
            await interaction.followup.send(f"Anúncio **#{aid}** salvo.", ephemeral=True)
        elif action_id == "e10":
            if not isinstance(interaction.channel, discord.TextChannel):
                await interaction.followup.send("Canal inválido.", ephemeral=True)
                return
            mins = _parse_int(gv(0), "Minutos")
            fire = (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
            rid = await bot.db.reminder_add(gid, interaction.channel.id, m.id, gv(1), fire)
            await interaction.followup.send(f"Lembrete **#{rid}**.", ephemeral=True)
        elif action_id == "e12":
            ok = await bot.db.reminder_delete_for_guild(gid, _parse_int(gv(0), "ID lembrete"))
            await interaction.followup.send("Cancelado." if ok else "ID inválido.", ephemeral=True)
        elif action_id == "e13":
            parts = [p.strip() for p in gv(1).split("|") if p.strip()]
            if len(parts) < 2:
                await interaction.followup.send("Mínimo 2 opções separadas por | .", ephemeral=True)
                return
            pid = await bot.db.poll_create(gid, gv(0), parts[:5], m.id)
            await interaction.followup.send(f"Enquete **#{pid}** criada (veja canal).", ephemeral=True)
            if isinstance(interaction.channel, discord.TextChannel):
                lines = "\n".join(f"{i}. {o}" for i, o in enumerate(parts[:5]))
                emb = discord.Embed(title=f"Enquete #{pid}", description=f"**{gv(0)}**\n\n{lines}")
                await interaction.channel.send(embed=emb)
        elif action_id == "e14":
            pid = _parse_int(gv(0), "ID enquete")
            poll = await bot.db.poll_get(pid)
            if not poll or poll.get("closed"):
                await interaction.followup.send("Enquete inválida.", ephemeral=True)
                return
            opts = json.loads(poll["options_json"])
            idx = _parse_int(gv(1), "Índice da opção")
            if idx >= len(opts):
                await interaction.followup.send("Índice inválido.", ephemeral=True)
                return
            await bot.db.poll_vote(pid, m.id, idx)
            await interaction.followup.send(f"Voto: **{opts[idx]}**", ephemeral=True)
        elif action_id == "e15":
            t = await bot.db.poll_tally(_parse_int(gv(0), "ID enquete"))
            if not t:
                await interaction.followup.send("Não encontrada.", ephemeral=True)
                return
            lines = [f"{i}. **{o}** — {t['counts'].get(i, 0)}" for i, o in enumerate(t["options"])]
            await interaction.followup.send("\n".join(lines), ephemeral=True)
        elif action_id == "e16":
            ok = await bot.db.poll_close(gid, _parse_int(gv(0), "ID enquete"))
            await interaction.followup.send("Encerrada." if ok else "Não encontrada.", ephemeral=True)
        elif action_id == "e17":
            ordem = _parse_int(gv(1), "Ordem") if gv(1).strip() else 0
            await bot.db.add_roster_role(gid, gv(0), _opt(gv(2)), ordem)
            await interaction.followup.send("Papel salvo.", ephemeral=True)
        elif action_id == "e19":
            if isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.send(gv(0)[:2000])
            await interaction.followup.send("Enviado.", ephemeral=True)
        elif action_id == "e20":
            try:
                col = int(gv(2).lstrip("#"), 16)
            except ValueError:
                col = 0x3498DB
            emb = discord.Embed(title=gv(0), description=gv(1), color=discord.Color(col))
            if isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.send(embed=emb)
            await interaction.followup.send("Embed publicado.", ephemeral=True)
        elif action_id == "s01":
            sid = await bot.db.add_strike(gid, _parse_int(gv(0), "ID membro"), gv(1), m.id)
            await interaction.followup.send(f"Strike **#{sid}**.", ephemeral=True)
        elif action_id == "s02":
            rows = await bot.db.list_strikes(gid, _parse_int(gv(0), "ID membro"))
            await interaction.followup.send(
                "\n".join(f"#{r['id']}: {r['reason']}" for r in rows[:8]) or "Sem strikes.",
                ephemeral=True,
            )
        elif action_id == "s03":
            n = await bot.db.clear_strikes(gid, _parse_int(gv(0), "ID membro"))
            await interaction.followup.send(f"Removidos: **{n}**.", ephemeral=True)
        elif action_id == "s04":
            await bot.db.blacklist_add(gid, _parse_int(gv(0), "ID usuário"), _opt(gv(1)), m.id)
            await interaction.followup.send("Adicionado à lista negra.", ephemeral=True)
        elif action_id == "s05":
            ok = await bot.db.blacklist_remove(gid, _parse_int(gv(0), "ID usuário"))
            await interaction.followup.send("Removido." if ok else "Não estava.", ephemeral=True)
        elif action_id == "s08":
            gp = _opt_int(gv(1))
            aid = await bot.db.create_application(gid, m.id, gv(0) or None, gp, _opt(gv(2)))
            cfg = await bot.db.get_guild_config(gid)
            ch_id = cfg.get("recruit_channel_id")
            if ch_id and interaction.guild:
                ch = interaction.guild.get_channel(int(ch_id))
                if isinstance(ch, discord.TextChannel):
                    emb = discord.Embed(title=f"Candidatura #{aid}", description=m.mention)
                    emb.add_field(name="IGN", value=gv(0) or "—")
                    await ch.send(embed=emb)
            await interaction.followup.send(f"Candidatura **#{aid}** enviada.", ephemeral=True)
        elif action_id == "s09":
            st = _opt(gv(0))
            rows = await bot.db.list_applications(gid, st)
            await interaction.followup.send(
                "\n".join(f"#{r['id']} <@{r['user_id']}> {r.get('status')}" for r in rows[:12]) or "Vazio.",
                ephemeral=True,
            )
        elif action_id == "s10":
            ok = await bot.db.review_application(gid, _parse_int(gv(0), "ID candidatura"), "aprovada", m.id)
            await interaction.followup.send("Aprovada." if ok else "ID inválido.", ephemeral=True)
        elif action_id == "s11":
            ok = await bot.db.review_application(gid, _parse_int(gv(0), "ID candidatura"), "recusada", m.id)
            await interaction.followup.send("Recusada." if ok else "ID inválido.", ephemeral=True)
        elif action_id == "s14":
            mid = await bot.db.create_goal(
                gid, gv(0), _parse_int(gv(1), "Alvo numérico"), gv(2) or "rep", _opt(gv(3))
            )
            await interaction.followup.send(f"Meta **#{mid}** criada.", ephemeral=True)
        elif action_id == "s16":
            ok = await bot.db.update_goal_progress(
                gid, _parse_int(gv(0), "ID meta"), _parse_int(gv(1), "Delta")
            )
            await interaction.followup.send("OK." if ok else "Meta não encontrada.", ephemeral=True)
        elif action_id == "s17":
            ok = await bot.db.delete_goal(gid, _parse_int(gv(0), "ID meta"))
            await interaction.followup.send("Apagada." if ok else "Não encontrada.", ephemeral=True)
        elif action_id == "s18":
            ch = interaction.channel
            if not isinstance(ch, discord.TextChannel):
                await interaction.followup.send("Use em canal texto.", ephemeral=True)
                return
            n = _parse_int(gv(0), "Quantidade")
            deleted = await ch.purge(limit=n)
            await interaction.followup.send(f"Removidas **{len(deleted)}**.", ephemeral=True)
        elif action_id == "s19":
            if not interaction.guild:
                return
            role = interaction.guild.get_role(_parse_int(gv(0), "ID do cargo"))
            if not role:
                await interaction.followup.send("Cargo não encontrado.", ephemeral=True)
                return
            mems = [x.mention for x in interaction.guild.members if role in x.roles][:20]
            await interaction.followup.send(", ".join(mems) or "Ninguém.", ephemeral=True)
        elif action_id == "k01":
            res = gv(1).strip().lower()
            if res not in {"vitória", "vitoria", "derrota", "empate"}:
                await interaction.followup.send("Resultado: vitória, derrota ou empate.", ephemeral=True)
                return
            res_db = "vitória" if res == "vitoria" else res
            su = _opt_int(gv(3))
            st = _opt_int(gv(4))
            wid = await bot.db.war_add(gid, gv(0), res_db, su, st, _opt(gv(5)), gv(2), m.id)
            await interaction.followup.send(f"Guerra **#{wid}** registrada.", ephemeral=True)
        elif action_id == "k03":
            coach = _opt_int(gv(2))
            tid = await bot.db.training_add(gid, gv(0), gv(1), coach, _opt(gv(3)))
            await interaction.followup.send(f"Treino **#{tid}**.", ephemeral=True)
        elif action_id == "k05":
            pid = await bot.db.sponsor_add(gid, gv(0), _opt(gv(1)), _opt(gv(2)), _opt(gv(3)), _opt(gv(4)))
            await interaction.followup.send(f"Patrocínio **#{pid}**.", ephemeral=True)
        elif action_id == "k07":
            assign = _opt_int(gv(1))
            tid = await bot.db.task_add(gid, gv(0), assign, _opt(gv(2)), m.id)
            await interaction.followup.send(f"Tarefa **#{tid}**.", ephemeral=True)
        elif action_id == "k08":
            st = _opt(gv(0))
            rows = await bot.db.task_list(gid, st)
            await interaction.followup.send(
                "\n".join(f"#{r['id']} {r['title']} [{r.get('status')}]" for r in rows[:15]) or "Vazio.",
                ephemeral=True,
            )
        elif action_id == "k09":
            ok = await bot.db.task_update_status(gid, _parse_int(gv(0), "ID tarefa"), gv(1))
            await interaction.followup.send("Atualizado." if ok else "Não encontrado.", ephemeral=True)
        else:
            await interaction.followup.send("Modal não tratado.", ephemeral=True)

        if interaction.guild and action_id not in {"e19", "e20", "e13", "e06"}:
            await refresh_panel_message(bot, interaction.guild)
    except ValueError as err:
        await interaction.followup.send(str(err), ephemeral=True)
    except Exception:
        log.exception("dispatch_modal %s", action_id)
        await interaction.followup.send("Erro ao processar o formulário.", ephemeral=True)
