"""Carrega configuração a partir de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_owner_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.replace(" ", "").split(","):
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int | None
    owner_ids: set[int]
    bot_name: str


def load_settings() -> Settings:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    gid = os.getenv("DISCORD_GUILD_ID", "").strip()
    guild_id = int(gid) if gid.isdigit() else None
    owners = _parse_owner_ids(os.getenv("BOT_OWNER_IDS"))
    name = os.getenv("BOT_NAME", "Asphalt9ClubBot").strip() or "Asphalt9ClubBot"
    return Settings(
        token=token,
        guild_id=guild_id,
        owner_ids=owners,
        bot_name=name,
    )
