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


def _parse_logo_urls(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(u.strip() for u in raw.split(",") if u.strip())


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int | None
    owner_ids: set[int]
    bot_name: str
    legion_name: str
    panel_channel_id: int | None
    logo_frame_urls: tuple[str, ...]
    logo_cycle_seconds: int


def load_settings() -> Settings:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    gid = os.getenv("DISCORD_GUILD_ID", "").strip()
    guild_id = int(gid) if gid.isdigit() else None
    owners = _parse_owner_ids(os.getenv("BOT_OWNER_IDS"))
    name = os.getenv("BOT_NAME", "Asphalt9ClubBot").strip() or "Asphalt9ClubBot"
    legion = os.getenv("LEGION_NAME", "Legião Espartan").strip() or "Legião Espartan"
    pch = os.getenv("PANEL_CHANNEL_ID", "").strip()
    panel_channel_id = int(pch) if pch.isdigit() else None
    logo_urls = _parse_logo_urls(os.getenv("PANEL_LOGO_URLS"))
    cycle_raw = os.getenv("LOGO_CYCLE_SECONDS", "4").strip()
    try:
        logo_cycle_seconds = max(2, min(60, int(cycle_raw)))
    except ValueError:
        logo_cycle_seconds = 4
    return Settings(
        token=token,
        guild_id=guild_id,
        owner_ids=owners,
        bot_name=name,
        legion_name=legion,
        panel_channel_id=panel_channel_id,
        logo_frame_urls=logo_urls,
        logo_cycle_seconds=logo_cycle_seconds,
    )
