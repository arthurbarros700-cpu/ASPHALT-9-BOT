"""Persistência SQLite assíncrona para o clube Asphalt 9."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

import aiosqlite


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str = "asphalt9_club.sqlite3") -> None:
        self._path = path

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA foreign_keys = ON;")
        await self._init_schema()
        await self._migrate_guild_config_columns()

    async def close(self) -> None:
        await self._db.close()

    async def _init_schema(self) -> None:
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                club_name TEXT,
                club_tag TEXT,
                timezone TEXT DEFAULT 'America/Sao_Paulo',
                rep_channel_id INTEGER,
                event_channel_id INTEGER,
                recruit_channel_id INTEGER,
                rules_text TEXT,
                created_at TEXT NOT NULL,
                panel_message_id INTEGER,
                panel_logo_index INTEGER DEFAULT 0,
                panel_logo_urls_json TEXT
            );

            CREATE TABLE IF NOT EXISTS members (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                nickname TEXT,
                role TEXT DEFAULT 'Membro',
                rep_week INTEGER DEFAULT 0,
                rep_total INTEGER DEFAULT 0,
                notes TEXT,
                joined_at TEXT NOT NULL,
                last_active TEXT,
                garage_json TEXT DEFAULT '{}',
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                starts_at TEXT NOT NULL,
                ends_at TEXT,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS event_rsvp (
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (event_id, user_id),
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS strikes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                ign TEXT,
                garage_power INTEGER,
                message TEXT,
                status TEXT DEFAULT 'aberta',
                created_at TEXT NOT NULL,
                reviewed_by INTEGER,
                reviewed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                target_value INTEGER NOT NULL,
                current_value INTEGER DEFAULT 0,
                unit TEXT DEFAULT 'rep',
                deadline TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                payload TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS roster_roles (
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, name)
            );

            CREATE TABLE IF NOT EXISTS blacklist (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS car_templates (
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                stars INTEGER DEFAULT 0,
                car_class TEXT DEFAULT 'D',
                PRIMARY KEY (guild_id, name)
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                fire_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                options_json TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                closed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS poll_votes (
                poll_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                option_index INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (poll_id, user_id),
                FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS war_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                opponent TEXT NOT NULL,
                result TEXT NOT NULL,
                score_us INTEGER,
                score_them INTEGER,
                notes TEXT,
                war_date TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS training_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                coach_id INTEGER,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sponsor_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                partner TEXT NOT NULL,
                value_text TEXT,
                starts_at TEXT,
                ends_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                assignee_id INTEGER,
                due_at TEXT,
                status TEXT DEFAULT 'aberta',
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS nick_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                old_ign TEXT,
                new_ign TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                changed_by INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_members_guild ON members(guild_id);
            CREATE INDEX IF NOT EXISTS idx_events_guild ON events(guild_id);
            CREATE INDEX IF NOT EXISTS idx_strikes_user ON strikes(guild_id, user_id);
            """
        )
        await self._db.commit()

    async def _migrate_guild_config_columns(self) -> None:
        cur = await self._db.execute("PRAGMA table_info(guild_config)")
        rows = await cur.fetchall()
        names = {r[1] for r in rows}
        alters: list[str] = []
        if "panel_message_id" not in names:
            alters.append("ALTER TABLE guild_config ADD COLUMN panel_message_id INTEGER")
        if "panel_logo_index" not in names:
            alters.append("ALTER TABLE guild_config ADD COLUMN panel_logo_index INTEGER DEFAULT 0")
        if "panel_logo_urls_json" not in names:
            alters.append("ALTER TABLE guild_config ADD COLUMN panel_logo_urls_json TEXT")
        for sql in alters:
            await self._db.execute(sql)
        if alters:
            await self._db.commit()

    async def audit(self, guild_id: int, actor_id: int, action: str, payload: dict | None = None) -> None:
        await self._db.execute(
            "INSERT INTO audit_log (guild_id, actor_id, action, payload, created_at) VALUES (?,?,?,?,?)",
            (guild_id, actor_id, action, json.dumps(payload or {}, ensure_ascii=False), _utc_now()),
        )
        await self._db.commit()

    async def get_guild_config(self, guild_id: int) -> dict[str, Any]:
        cur = await self._db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
        row = await cur.fetchone()
        if row is None:
            await self._db.execute(
                "INSERT INTO guild_config (guild_id, created_at) VALUES (?,?)",
                (guild_id, _utc_now()),
            )
            await self._db.commit()
            cur = await self._db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
            row = await cur.fetchone()
        return dict(row)

    async def set_club_identity(self, guild_id: int, name: str | None, tag: str | None) -> None:
        cfg = await self.get_guild_config(guild_id)
        new_name = name if name is not None else cfg.get("club_name")
        new_tag = tag if tag is not None else cfg.get("club_tag")
        await self._db.execute(
            "UPDATE guild_config SET club_name = ?, club_tag = ? WHERE guild_id = ?",
            (new_name, new_tag, guild_id),
        )
        await self._db.commit()

    async def set_guild_timezone(self, guild_id: int, tz: str) -> None:
        await self._db.execute(
            "UPDATE guild_config SET timezone = ? WHERE guild_id = ?",
            (tz, guild_id),
        )
        await self._db.commit()

    async def set_channel_prefs(
        self,
        guild_id: int,
        rep_channel_id: int | None = None,
        event_channel_id: int | None = None,
        recruit_channel_id: int | None = None,
    ) -> None:
        cfg = await self.get_guild_config(guild_id)
        await self._db.execute(
            """
            UPDATE guild_config SET
                rep_channel_id = COALESCE(?, rep_channel_id),
                event_channel_id = COALESCE(?, event_channel_id),
                recruit_channel_id = COALESCE(?, recruit_channel_id)
            WHERE guild_id = ?
            """,
            (
                rep_channel_id if rep_channel_id is not None else cfg.get("rep_channel_id"),
                event_channel_id if event_channel_id is not None else cfg.get("event_channel_id"),
                recruit_channel_id if recruit_channel_id is not None else cfg.get("recruit_channel_id"),
                guild_id,
            ),
        )
        await self._db.commit()

    async def set_rules(self, guild_id: int, text: str) -> None:
        await self._db.execute(
            "UPDATE guild_config SET rules_text = ? WHERE guild_id = ?",
            (text, guild_id),
        )
        await self._db.commit()

    async def set_panel_message(self, guild_id: int, message_id: int | None) -> None:
        await self._db.execute(
            "UPDATE guild_config SET panel_message_id = ? WHERE guild_id = ?",
            (message_id, guild_id),
        )
        await self._db.commit()

    async def get_panel_message_id(self, guild_id: int) -> int | None:
        cfg = await self.get_guild_config(guild_id)
        mid = cfg.get("panel_message_id")
        return int(mid) if mid is not None else None

    async def set_panel_logo_state(self, guild_id: int, frame_index: int, urls_json: str | None) -> None:
        await self._db.execute(
            "UPDATE guild_config SET panel_logo_index = ?, panel_logo_urls_json = ? WHERE guild_id = ?",
            (frame_index, urls_json, guild_id),
        )
        await self._db.commit()

    async def get_panel_logo_state(self, guild_id: int) -> tuple[int, str | None]:
        cfg = await self.get_guild_config(guild_id)
        idx = int(cfg.get("panel_logo_index") or 0)
        raw = cfg.get("panel_logo_urls_json")
        return idx, raw if isinstance(raw, str) else None

    async def upsert_member(
        self,
        guild_id: int,
        user_id: int,
        nickname: str | None = None,
        role: str | None = None,
    ) -> None:
        now = _utc_now()
        cur = await self._db.execute(
            "SELECT 1 FROM members WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        exists = await cur.fetchone()
        if exists:
            if nickname is not None:
                await self._db.execute(
                    "UPDATE members SET nickname = ?, last_active = ? WHERE guild_id = ? AND user_id = ?",
                    (nickname, now, guild_id, user_id),
                )
            if role is not None:
                await self._db.execute(
                    "UPDATE members SET role = ? WHERE guild_id = ? AND user_id = ?",
                    (role, guild_id, user_id),
                )
        else:
            await self._db.execute(
                """
                INSERT INTO members (guild_id, user_id, nickname, role, joined_at, last_active)
                VALUES (?,?,?,?,?,?)
                """,
                (guild_id, user_id, nickname, role or "Membro", now, now),
            )
        await self._db.commit()

    async def get_member(self, guild_id: int, user_id: int) -> dict[str, Any] | None:
        cur = await self._db.execute(
            "SELECT * FROM members WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def list_members(self, guild_id: int, limit: int = 50) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM members WHERE guild_id = ? ORDER BY rep_total DESC LIMIT ?",
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def subtract_rep(self, guild_id: int, user_id: int, amount: int) -> dict[str, Any] | None:
        m = await self.get_member(guild_id, user_id)
        if not m:
            return None
        new_week = max(0, int(m["rep_week"] or 0) - amount)
        new_total = max(0, int(m["rep_total"] or 0) - amount)
        await self._db.execute(
            "UPDATE members SET rep_week = ?, rep_total = ?, last_active = ? WHERE guild_id = ? AND user_id = ?",
            (new_week, new_total, _utc_now(), guild_id, user_id),
        )
        await self._db.commit()
        return await self.get_member(guild_id, user_id)

    async def add_rep(self, guild_id: int, user_id: int, amount: int) -> dict[str, Any]:
        m = await self.get_member(guild_id, user_id)
        if not m:
            await self.upsert_member(guild_id, user_id)
            m = await self.get_member(guild_id, user_id)
        assert m is not None
        new_week = int(m["rep_week"] or 0) + amount
        new_total = int(m["rep_total"] or 0) + amount
        await self._db.execute(
            "UPDATE members SET rep_week = ?, rep_total = ?, last_active = ? WHERE guild_id = ? AND user_id = ?",
            (new_week, new_total, _utc_now(), guild_id, user_id),
        )
        await self._db.commit()
        return await self.get_member(guild_id, user_id)  # type: ignore[return-value]

    async def set_rep_week(self, guild_id: int, user_id: int, value: int) -> None:
        await self._db.execute(
            "UPDATE members SET rep_week = ? WHERE guild_id = ? AND user_id = ?",
            (value, guild_id, user_id),
        )
        await self._db.commit()

    async def reset_week_rep(self, guild_id: int) -> int:
        cur = await self._db.execute(
            "UPDATE members SET rep_week = 0 WHERE guild_id = ?",
            (guild_id,),
        )
        await self._db.commit()
        return cur.rowcount or 0

    async def set_member_notes(self, guild_id: int, user_id: int, notes: str) -> None:
        await self._db.execute(
            "UPDATE members SET notes = ? WHERE guild_id = ? AND user_id = ?",
            (notes, guild_id, user_id),
        )
        await self._db.commit()

    async def set_member_role_name(self, guild_id: int, user_id: int, role_name: str) -> None:
        await self._db.execute(
            "UPDATE members SET role = ? WHERE guild_id = ? AND user_id = ?",
            (role_name, guild_id, user_id),
        )
        await self._db.commit()

    async def remove_member(self, guild_id: int, user_id: int) -> None:
        await self._db.execute(
            "DELETE FROM members WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self._db.commit()

    async def garage_get(self, guild_id: int, user_id: int) -> dict[str, Any]:
        m = await self.get_member(guild_id, user_id)
        if not m:
            return {}
        raw = m.get("garage_json") or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    async def garage_set_field(self, guild_id: int, user_id: int, key: str, value: Any) -> dict[str, Any]:
        g = await self.garage_get(guild_id, user_id)
        g[key] = value
        await self._db.execute(
            "UPDATE members SET garage_json = ? WHERE guild_id = ? AND user_id = ?",
            (json.dumps(g, ensure_ascii=False), guild_id, user_id),
        )
        await self._db.commit()
        return g

    async def garage_delete_field(self, guild_id: int, user_id: int, key: str) -> bool:
        g = await self.garage_get(guild_id, user_id)
        if key not in g:
            return False
        del g[key]
        await self._db.execute(
            "UPDATE members SET garage_json = ? WHERE guild_id = ? AND user_id = ?",
            (json.dumps(g, ensure_ascii=False), guild_id, user_id),
        )
        await self._db.commit()
        return True

    async def create_event(
        self,
        guild_id: int,
        title: str,
        starts_at: str,
        created_by: int,
        description: str | None = None,
        ends_at: str | None = None,
    ) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO events (guild_id, title, description, starts_at, ends_at, created_by, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (guild_id, title, description, starts_at, ends_at, created_by, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def list_events(self, guild_id: int, limit: int = 10) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM events WHERE guild_id = ? ORDER BY starts_at ASC LIMIT ?",
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def get_event(self, guild_id: int, event_id: int) -> dict[str, Any] | None:
        cur = await self._db.execute(
            "SELECT * FROM events WHERE guild_id = ? AND id = ?",
            (guild_id, event_id),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def delete_event(self, guild_id: int, event_id: int) -> bool:
        cur = await self._db.execute(
            "DELETE FROM events WHERE id = ? AND guild_id = ?",
            (event_id, guild_id),
        )
        await self._db.commit()
        return (cur.rowcount or 0) > 0

    async def rsvp_set(self, event_id: int, user_id: int, status: str) -> None:
        await self._db.execute(
            """
            INSERT INTO event_rsvp (event_id, user_id, status, updated_at)
            VALUES (?,?,?,?)
            ON CONFLICT(event_id, user_id) DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at
            """,
            (event_id, user_id, status, _utc_now()),
        )
        await self._db.commit()

    async def rsvp_list(self, event_id: int) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM event_rsvp WHERE event_id = ?",
            (event_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def add_strike(self, guild_id: int, user_id: int, reason: str, created_by: int) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO strikes (guild_id, user_id, reason, created_by, created_at)
            VALUES (?,?,?,?,?)
            """,
            (guild_id, user_id, reason, created_by, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def list_strikes(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM strikes WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (guild_id, user_id),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def clear_strikes(self, guild_id: int, user_id: int) -> int:
        cur = await self._db.execute(
            "DELETE FROM strikes WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self._db.commit()
        return cur.rowcount or 0

    async def create_application(
        self,
        guild_id: int,
        user_id: int,
        ign: str | None,
        garage_power: int | None,
        message: str | None,
    ) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO applications (guild_id, user_id, ign, garage_power, message, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (guild_id, user_id, ign, garage_power, message, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def list_applications(self, guild_id: int, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            cur = await self._db.execute(
                "SELECT * FROM applications WHERE guild_id = ? AND status = ? ORDER BY id DESC LIMIT 25",
                (guild_id, status),
            )
        else:
            cur = await self._db.execute(
                "SELECT * FROM applications WHERE guild_id = ? ORDER BY id DESC LIMIT 25",
                (guild_id,),
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def review_application(
        self,
        guild_id: int,
        app_id: int,
        new_status: str,
        reviewer_id: int,
    ) -> bool:
        cur = await self._db.execute(
            """
            UPDATE applications SET status = ?, reviewed_by = ?, reviewed_at = ?
            WHERE id = ? AND guild_id = ?
            """,
            (new_status, reviewer_id, _utc_now(), app_id, guild_id),
        )
        await self._db.commit()
        return (cur.rowcount or 0) > 0

    async def create_goal(
        self,
        guild_id: int,
        title: str,
        target_value: int,
        unit: str,
        deadline: str | None,
    ) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO goals (guild_id, title, target_value, unit, deadline, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (guild_id, title, target_value, unit, deadline, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def list_goals(self, guild_id: int) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM goals WHERE guild_id = ? ORDER BY id DESC LIMIT 20",
            (guild_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def update_goal_progress(self, guild_id: int, goal_id: int, delta: int) -> bool:
        cur = await self._db.execute(
            """
            UPDATE goals SET current_value = current_value + ?
            WHERE id = ? AND guild_id = ?
            """,
            (delta, goal_id, guild_id),
        )
        await self._db.commit()
        return (cur.rowcount or 0) > 0

    async def delete_goal(self, guild_id: int, goal_id: int) -> bool:
        cur = await self._db.execute(
            "DELETE FROM goals WHERE id = ? AND guild_id = ?",
            (goal_id, guild_id),
        )
        await self._db.commit()
        return (cur.rowcount or 0) > 0

    async def create_announcement(self, guild_id: int, title: str, body: str, created_by: int) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO announcements (guild_id, title, body, created_by, created_at)
            VALUES (?,?,?,?,?)
            """,
            (guild_id, title, body, created_by, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def list_announcements(self, guild_id: int, limit: int = 5) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM announcements WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def add_roster_role(self, guild_id: int, name: str, description: str | None, sort_order: int) -> None:
        await self._db.execute(
            """
            INSERT OR REPLACE INTO roster_roles (guild_id, name, description, sort_order)
            VALUES (?,?,?,?)
            """,
            (guild_id, name, description, sort_order),
        )
        await self._db.commit()

    async def list_roster_roles(self, guild_id: int) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM roster_roles WHERE guild_id = ? ORDER BY sort_order ASC, name ASC",
            (guild_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def blacklist_add(self, guild_id: int, user_id: int, reason: str | None, created_by: int) -> None:
        await self._db.execute(
            """
            INSERT OR REPLACE INTO blacklist (guild_id, user_id, reason, created_by, created_at)
            VALUES (?,?,?,?,?)
            """,
            (guild_id, user_id, reason, created_by, _utc_now()),
        )
        await self._db.commit()

    async def blacklist_remove(self, guild_id: int, user_id: int) -> bool:
        cur = await self._db.execute(
            "DELETE FROM blacklist WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self._db.commit()
        return (cur.rowcount or 0) > 0

    async def blacklist_list(self, guild_id: int) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM blacklist WHERE guild_id = ? ORDER BY created_at DESC LIMIT 50",
            (guild_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def car_template_add(self, guild_id: int, name: str, stars: int, car_class: str) -> None:
        await self._db.execute(
            """
            INSERT OR REPLACE INTO car_templates (guild_id, name, stars, car_class)
            VALUES (?,?,?,?)
            """,
            (guild_id, name, stars, car_class),
        )
        await self._db.commit()

    async def car_templates_list(self, guild_id: int) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM car_templates WHERE guild_id = ? ORDER BY car_class ASC, stars DESC, name ASC LIMIT 100",
            (guild_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def reminder_add(self, guild_id: int, channel_id: int, author_id: int, message: str, fire_at: str) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO reminders (guild_id, channel_id, author_id, message, fire_at, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (guild_id, channel_id, author_id, message, fire_at, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def due_reminders(self, before_iso: str) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM reminders WHERE fire_at <= ? ORDER BY fire_at ASC LIMIT 20",
            (before_iso,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def reminder_delete(self, reminder_id: int) -> None:
        await self._db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await self._db.commit()

    async def reminder_list_guild(self, guild_id: int, limit: int = 15) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM reminders WHERE guild_id = ? ORDER BY fire_at ASC LIMIT ?",
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def reminder_delete_for_guild(self, guild_id: int, reminder_id: int) -> bool:
        cur = await self._db.execute(
            "DELETE FROM reminders WHERE id = ? AND guild_id = ?",
            (reminder_id, guild_id),
        )
        await self._db.commit()
        return (cur.rowcount or 0) > 0

    async def poll_create(self, guild_id: int, question: str, options: list[str], created_by: int) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO polls (guild_id, question, options_json, created_by, created_at)
            VALUES (?,?,?,?,?)
            """,
            (guild_id, question, json.dumps(options, ensure_ascii=False), created_by, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def poll_get(self, poll_id: int) -> dict[str, Any] | None:
        cur = await self._db.execute("SELECT * FROM polls WHERE id = ?", (poll_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def poll_vote(self, poll_id: int, user_id: int, option_index: int) -> None:
        await self._db.execute(
            """
            INSERT INTO poll_votes (poll_id, user_id, option_index, updated_at)
            VALUES (?,?,?,?)
            ON CONFLICT(poll_id, user_id) DO UPDATE SET option_index = excluded.option_index, updated_at = excluded.updated_at
            """,
            (poll_id, user_id, option_index, _utc_now()),
        )
        await self._db.commit()

    async def poll_tally(self, poll_id: int) -> dict[str, Any]:
        poll = await self.poll_get(poll_id)
        if not poll:
            return {}
        options: list[str] = json.loads(poll["options_json"])
        cur = await self._db.execute(
            "SELECT option_index, COUNT(*) AS c FROM poll_votes WHERE poll_id = ? GROUP BY option_index",
            (poll_id,),
        )
        rows = await cur.fetchall()
        counts = {int(r["option_index"]): int(r["c"]) for r in rows}
        return {"options": options, "counts": counts, "closed": bool(poll.get("closed"))}

    async def poll_close(self, guild_id: int, poll_id: int) -> bool:
        cur = await self._db.execute(
            "UPDATE polls SET closed = 1 WHERE id = ? AND guild_id = ?",
            (poll_id, guild_id),
        )
        await self._db.commit()
        return (cur.rowcount or 0) > 0

    async def war_add(
        self,
        guild_id: int,
        opponent: str,
        result: str,
        score_us: int | None,
        score_them: int | None,
        notes: str | None,
        war_date: str,
        created_by: int,
    ) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO war_history (guild_id, opponent, result, score_us, score_them, notes, war_date, created_by, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (guild_id, opponent, result, score_us, score_them, notes, war_date, created_by, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def war_list(self, guild_id: int, limit: int = 10) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM war_history WHERE guild_id = ? ORDER BY war_date DESC LIMIT ?",
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def training_add(
        self,
        guild_id: int,
        topic: str,
        scheduled_at: str,
        coach_id: int | None,
        notes: str | None,
    ) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO training_sessions (guild_id, topic, scheduled_at, coach_id, notes, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (guild_id, topic, scheduled_at, coach_id, notes, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def training_list(self, guild_id: int, limit: int = 10) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM training_sessions WHERE guild_id = ? ORDER BY scheduled_at ASC LIMIT ?",
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def sponsor_add(
        self,
        guild_id: int,
        partner: str,
        value_text: str | None,
        starts_at: str | None,
        ends_at: str | None,
        notes: str | None,
    ) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO sponsor_deals (guild_id, partner, value_text, starts_at, ends_at, notes, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (guild_id, partner, value_text, starts_at, ends_at, notes, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def sponsor_list(self, guild_id: int, limit: int = 10) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM sponsor_deals WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def task_add(
        self,
        guild_id: int,
        title: str,
        assignee_id: int | None,
        due_at: str | None,
        created_by: int,
    ) -> int:
        cur = await self._db.execute(
            """
            INSERT INTO tasks (guild_id, title, assignee_id, due_at, created_by, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (guild_id, title, assignee_id, due_at, created_by, _utc_now()),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def task_list(self, guild_id: int, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            cur = await self._db.execute(
                "SELECT * FROM tasks WHERE guild_id = ? AND status = ? ORDER BY id DESC LIMIT 30",
                (guild_id, status),
            )
        else:
            cur = await self._db.execute(
                "SELECT * FROM tasks WHERE guild_id = ? ORDER BY id DESC LIMIT 30",
                (guild_id,),
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def task_update_status(self, guild_id: int, task_id: int, status: str) -> bool:
        cur = await self._db.execute(
            "UPDATE tasks SET status = ? WHERE id = ? AND guild_id = ?",
            (status, task_id, guild_id),
        )
        await self._db.commit()
        return (cur.rowcount or 0) > 0

    async def nick_log(
        self,
        guild_id: int,
        user_id: int,
        old_ign: str | None,
        new_ign: str,
        changed_by: int,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO nick_history (guild_id, user_id, old_ign, new_ign, changed_at, changed_by)
            VALUES (?,?,?,?,?,?)
            """,
            (guild_id, user_id, old_ign, new_ign, _utc_now(), changed_by),
        )
        await self._db.commit()

    async def nick_history_list(self, guild_id: int, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            """
            SELECT * FROM nick_history WHERE guild_id = ? AND user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (guild_id, user_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def audit_recent(self, guild_id: int, limit: int = 15) -> list[dict[str, Any]]:
        cur = await self._db.execute(
            "SELECT * FROM audit_log WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
            (guild_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def leaderboard(self, guild_id: int, kind: str, limit: int = 10) -> Iterable[dict[str, Any]]:
        if kind == "semana":
            cur = await self._db.execute(
                "SELECT user_id, rep_week FROM members WHERE guild_id = ? ORDER BY rep_week DESC LIMIT ?",
                (guild_id, limit),
            )
        else:
            cur = await self._db.execute(
                "SELECT user_id, rep_total FROM members WHERE guild_id = ? ORDER BY rep_total DESC LIMIT ?",
                (guild_id, limit),
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def guild_row_counts(self, guild_id: int) -> dict[str, int]:
        out: dict[str, int] = {}
        for table in ("members", "events", "applications", "tasks", "strikes"):
            cur = await self._db.execute(
                f"SELECT COUNT(*) AS c FROM {table} WHERE guild_id = ?",
                (guild_id,),
            )
            row = await cur.fetchone()
            out[table] = int(row["c"]) if row and row["c"] is not None else 0
        return out

    async def export_snapshot(self, guild_id: int) -> dict[str, Any]:
        members = await self.list_members(guild_id, 500)
        events = await self.list_events(guild_id, 50)
        goals = await self.list_goals(guild_id)
        apps = await self.list_applications(guild_id, None)
        wars = await self.war_list(guild_id, 50)
        return {
            "exported_at": _utc_now(),
            "guild_id": guild_id,
            "members": members,
            "events": events,
            "goals": goals,
            "applications": apps,
            "wars": wars,
        }
