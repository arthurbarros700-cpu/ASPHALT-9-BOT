"""Garagem e templates de carros (referência para Asphalt 9)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from permissions import staff_only

if TYPE_CHECKING:
    from bot import Asphalt9Bot


class Garage(commands.Cog):
    def __init__(self, bot: Asphalt9Bot) -> None:
        self.bot = bot

    @app_commands.command(name="garagem_ver", description="Mostra dados de garagem salvos (JSON flexível).")
    async def garagem_ver(self, interaction: discord.Interaction, membro: discord.Member | None = None) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        m = membro or interaction.user
        if not isinstance(m, discord.Member):
            return await interaction.response.send_message("Membro inválido.", ephemeral=True)
        g = await self.bot.db.garage_get(interaction.guild.id, m.id)
        if not g:
            return await interaction.response.send_message("Garagem vazia. Use `/garagem_definir`.", ephemeral=True)
        raw = json.dumps(g, ensure_ascii=False, indent=2)[:1900]
        await interaction.response.send_message(f"```json\n{raw}\n```", ephemeral=True)

    @app_commands.command(name="garagem_definir", description="Define um campo chave/valor na sua garagem.")
    @app_commands.describe(chave="Ex.: classe_principal, carro_favorito, notas_gp", valor="Texto livre")
    async def garagem_definir(self, interaction: discord.Interaction, chave: str, valor: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.upsert_member(interaction.guild.id, interaction.user.id)
        await self.bot.db.garage_set_field(interaction.guild.id, interaction.user.id, chave, valor)
        await interaction.response.send_message(f"Campo `{chave}` atualizado.", ephemeral=True)

    @app_commands.command(name="garagem_poder", description="Atalho: salva poder total aproximado da garagem.")
    async def garagem_poder(
        self,
        interaction: discord.Interaction,
        poder: app_commands.Range[int, 0, 9999999],
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.upsert_member(interaction.guild.id, interaction.user.id)
        await self.bot.db.garage_set_field(interaction.guild.id, interaction.user.id, "poder", poder)
        await interaction.response.send_message(f"Poder da garagem salvo: **{poder}**.", ephemeral=True)

    @app_commands.command(name="template_carro_add", description="Catálogo interno: adiciona modelo de carro de referência.")
    @staff_only()
    async def template_carro_add(
        self,
        interaction: discord.Interaction,
        nome: str,
        estrelas: app_commands.Range[int, 0, 6],
        classe: str,
    ) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        await self.bot.db.car_template_add(interaction.guild.id, nome, estrelas, classe.upper()[:1])
        await interaction.response.send_message(f"Template **{nome}** salvo.", ephemeral=True)

    @app_commands.command(name="template_carros_listar", description="Lista templates cadastrados.")
    async def template_carros_listar(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        rows = await self.bot.db.car_templates_list(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message("Nenhum template.", ephemeral=True)
        lines = [f"**{r['name']}** · {r.get('stars')}★ · classe {r.get('car_class')}" for r in rows[:25]]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="garagem_limpar_campo", description="Remove um campo da sua garagem.")
    async def garagem_limpar_campo(self, interaction: discord.Interaction, chave: str) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Use em um servidor.", ephemeral=True)
        ok = await self.bot.db.garage_delete_field(interaction.guild.id, interaction.user.id, chave)
        await interaction.response.send_message(
            f"Campo `{chave}` removido." if ok else "Campo não encontrado.",
            ephemeral=True,
        )


async def setup(bot: Asphalt9Bot) -> None:
    await bot.add_cog(Garage(bot))
