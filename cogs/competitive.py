"""Competitivo: histórico de guerras/GP, treinos, patrocínios, tarefas."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Competitive(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="guerra_registrar", description="Registra resultado de guerra/GP de clube.")
    @staff_only()
    @app_commands.describe(
        adversario="Nome do clube adversário",
        resultado="vitória | derrota | empate",
        nosso_placar="Opcional",
        placar_adversario="Opcional",
        data_iso="Data da guerra (ISO)",
        notas="Contexto / MVP / observações",
    )
    async def guerra_registrar(
        self,
        interaction: discord.Interaction,
        adversario: str,
        resultado: str,
        data_iso: str,
        nosso_placar: int | None = None,
        placar_adversario: int | None = None,
        notas: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        res = resultado.strip().lower()
        if res not in {"vitória", "derrota", "empate"}:
            return await interaction.response.send_message("Resultado inválido.", ephemeral=True)
        wid = await self.bot.db.war_add(
            interaction.guild.id,
            adversario,
            res,
            nosso_placar,
            placar_adversario,
            notas,
            data_iso,
            interaction.user.id,
        )
        await interaction.response.send_message(f"Guerra **#{wid}** registrada.", ephemeral=True)

    @app_commands.command(name="guerras_historico", description="Últimas guerras registradas.")
    async def guerras_historico(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.war_list(interaction.guild.id, 12)
        if not rows:
            return await interaction.response.send_message("Sem registros.", ephemeral=True)
        lines = []
        for r in rows:
            sc = ""
            if r.get("score_us") is not None and r.get("score_them") is not None:
                sc = f" ({r['score_us']}x{r['score_them']})"
            lines.append(f"`{r['war_date'][:10]}` vs **{r['opponent']}** — {r['result']}{sc}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="treino_agendar", description="Agenda sessão de treino / estratégia.")
    @staff_only()
    async def treino_agendar(
        self,
        interaction: discord.Interaction,
        tema: str,
        quando_iso: str,
        treinador: discord.Member | None = None,
        notas: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        tid = await self.bot.db.training_add(
            interaction.guild.id,
            tema,
            quando_iso,
            treinador.id if treinador else None,
            notas,
        )
        await interaction.response.send_message(f"Treino **#{tid}** agendado.", ephemeral=True)

    @app_commands.command(name="treinos_listar", description="Próximos treinos agendados.")
    async def treinos_listar(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.training_list(interaction.guild.id, 12)
        if not rows:
            return await interaction.response.send_message("Sem treinos.", ephemeral=True)
        lines = [f"**#{r['id']}** {r['topic']} — `{r['scheduled_at']}`" for r in rows]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="patrocinio_add", description="Registra parceria / patrocínio interno.")
    @staff_only()
    async def patrocinio_add(
        self,
        interaction: discord.Interaction,
        parceiro: str,
        valor: str | None = None,
        inicio_iso: str | None = None,
        fim_iso: str | None = None,
        notas: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        pid = await self.bot.db.sponsor_add(interaction.guild.id, parceiro, valor, inicio_iso, fim_iso, notas)
        await interaction.response.send_message(f"Patrocínio **#{pid}** salvo.", ephemeral=True)

    @app_commands.command(name="patrocinios_listar", description="Últimos patrocínios registrados.")
    async def patrocinios_listar(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.sponsor_list(interaction.guild.id, 10)
        if not rows:
            return await interaction.response.send_message("Sem patrocínios.", ephemeral=True)
        lines = [f"**{r['partner']}** — {r.get('value_text') or '—'}" for r in rows]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="tarefa_criar", description="Cria tarefa operacional (staff).")
    @staff_only()
    async def tarefa_criar(
        self,
        interaction: discord.Interaction,
        titulo: str,
        responsavel: discord.Member | None = None,
        prazo_iso: str | None = None,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        tid = await self.bot.db.task_add(
            interaction.guild.id,
            titulo,
            responsavel.id if responsavel else None,
            prazo_iso,
            interaction.user.id,
        )
        await interaction.response.send_message(f"Tarefa **#{tid}** criada.", ephemeral=True)

    @app_commands.command(name="tarefas_listar", description="Lista tarefas recentes.")
    @staff_only()
    async def tarefas_listar(self, interaction: discord.Interaction, status: str | None = None) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.task_list(interaction.guild.id, status)
        if not rows:
            return await interaction.response.send_message("Sem tarefas.", ephemeral=True)
        lines = []
        for r in rows[:15]:
            who = f"<@{r['assignee_id']}>" if r.get("assignee_id") else "—"
            lines.append(f"**#{r['id']}** {r['title']} — {r.get('status')} — {who}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="tarefa_status", description="Atualiza status de uma tarefa.")
    @staff_only()
    async def tarefa_status(
        self,
        interaction: discord.Interaction,
        id: int,
        status: str,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.task_update_status(interaction.guild.id, id, status)
        await interaction.response.send_message("Atualizado." if ok else "Tarefa não encontrada.", ephemeral=True)

    @app_commands.command(name="calendario_dica", description="Boas práticas para datas ISO em eventos e treinos.")
    async def calendario_dica(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Use datas em **ISO 8601** com fuso, por exemplo `2026-04-10T20:00:00-03:00` ou `...Z` em UTC. "
            "Assim todos interpretam o mesmo instante.",
            ephemeral=True,
        )

    @app_commands.command(name="estrategia_modelo", description="Modelo de briefing tático para GP/clube.")
    @staff_only()
    async def estrategia_modelo(self, interaction: discord.Interaction) -> None:
        txt = (
            "**Briefing GP**\n"
            "1. Mapa / condições (nitro, curvas fechadas)\n"
            "2. Composição de equipe e papéis\n"
            "3. Comunicação (call / ping / ordem de ghost)\n"
            "4. Plano B se alguém cair\n"
        )
        await interaction.response.send_message(txt, ephemeral=True)


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Competitive(bot))
