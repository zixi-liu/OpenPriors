"""
Prior Storage

Stores priors as human-readable .md files and indexes them in SQLite.
Local-first: no cloud DB required.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.config import get_priors_dir, get_db_path


def _get_db() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT,
            source_type TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            author TEXT,
            session_id TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS priors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            principle TEXT NOT NULL,
            practice TEXT NOT NULL,
            trigger_context TEXT,
            source TEXT,
            source_title TEXT,
            material_id TEXT,
            file_path TEXT,
            created_at TEXT NOT NULL,
            last_practiced TEXT,
            practice_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (material_id) REFERENCES materials(id)
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS priors_fts
        USING fts5(name, principle, practice, source, content=priors, content_rowid=rowid)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            options TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    return conn


def save_material(
    title: str,
    content: str,
    source_type: str = "url",
    url: str = "",
    summary: str = "",
    author: str = "",
    session_id: str = "",
) -> str:
    """Save a learning material (transcript, article text, etc.) and return its ID."""
    material_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    conn = _get_db()
    conn.execute(
        """INSERT INTO materials (id, title, url, source_type, content, summary, author, session_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (material_id, title, url, source_type, content, summary, author, session_id, now),
    )
    conn.commit()
    conn.close()
    return material_id


def get_material(material_id: str) -> Optional[Dict[str, Any]]:
    """Get a material by ID."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_materials() -> List[Dict[str, Any]]:
    """Get all materials ordered by creation date."""
    conn = _get_db()
    rows = conn.execute("SELECT * FROM materials ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_material(material_id: str) -> bool:
    """Delete a material and its linked priors."""
    conn = _get_db()
    # Delete linked priors
    conn.execute("DELETE FROM priors WHERE material_id = ?", (material_id,))
    cursor = conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def save_prior(prior: Dict[str, Any], source_title: str = "", material_id: str = "") -> str:
    """Save a single prior as .md file and index in SQLite."""
    prior_id = str(uuid.uuid4())[:8]
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # Write .md file
    slug = prior["name"].lower().replace(" ", "-")[:30]
    filename = f"{date_str}-{slug}.md"
    priors_dir = get_priors_dir()
    priors_dir.mkdir(parents=True, exist_ok=True)
    filepath = priors_dir / filename

    md_content = f"""---
id: {prior_id}
name: {prior["name"]}
source: {prior.get("source", "")}
created: {now.isoformat()}
---

## {prior["name"]}

**Principle:** {prior["principle"]}

**Practice:** {prior["practice"]}

**When to apply:** {prior.get("trigger", "anytime")}

**Source:** {prior.get("source", "unknown")}
"""
    filepath.write_text(md_content)

    # Index in SQLite
    conn = _get_db()
    conn.execute(
        """INSERT INTO priors (id, name, principle, practice, trigger_context, source, source_title, material_id, file_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            prior_id,
            prior["name"],
            prior["principle"],
            prior["practice"],
            prior.get("trigger", ""),
            prior.get("source", ""),
            source_title,
            material_id,
            str(filepath),
            now.isoformat(),
        ),
    )
    # Update FTS index
    conn.execute(
        "INSERT INTO priors_fts (rowid, name, principle, practice, source) VALUES (last_insert_rowid(), ?, ?, ?, ?)",
        (prior["name"], prior["principle"], prior["practice"], prior.get("source", "")),
    )
    conn.commit()
    conn.close()
    return prior_id


def save_priors(priors: List[Dict[str, Any]], source_title: str = "", material_id: str = "") -> List[str]:
    """Save multiple priors. Returns list of IDs."""
    return [save_prior(p, source_title, material_id) for p in priors]


def get_all_priors(status: str = "active") -> List[Dict[str, Any]]:
    """Get all priors."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM priors WHERE status = ? ORDER BY created_at DESC", (status,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_priors(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Full-text search across priors."""
    conn = _get_db()
    rows = conn.execute(
        """SELECT p.* FROM priors p
           JOIN priors_fts fts ON p.rowid = fts.rowid
           WHERE priors_fts MATCH ? AND p.status = 'active'
           ORDER BY rank LIMIT ?""",
        (query, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_prior(prior_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM priors WHERE id = ?", (prior_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_priors_by_session(session_id: str) -> List[Dict[str, Any]]:
    """Get all priors linked to materials from a specific session."""
    conn = _get_db()
    rows = conn.execute(
        """SELECT p.*, m.title as material_title, m.summary as material_summary
           FROM priors p
           JOIN materials m ON p.material_id = m.id
           WHERE m.session_id = ? AND p.status = 'active'
           ORDER BY p.created_at ASC""",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_materials_by_session(session_id: str) -> List[Dict[str, Any]]:
    """Get all materials created in a specific session."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM materials WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_practice(prior_id: str):
    """Record that a prior was practiced."""
    conn = _get_db()
    conn.execute(
        """UPDATE priors SET practice_count = practice_count + 1,
           last_practiced = ? WHERE id = ?""",
        (datetime.now().isoformat(), prior_id),
    )
    conn.commit()
    conn.close()


# ============================================================
# Sessions
# ============================================================

def create_session(title: str = "New Page") -> str:
    session_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    conn = _get_db()
    conn.execute(
        "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (session_id, title, now, now),
    )
    conn.commit()
    conn.close()
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_sessions() -> List[Dict[str, Any]]:
    conn = _get_db()
    rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_session_title(session_id: str, title: str):
    conn = _get_db()
    conn.execute(
        "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
        (title, datetime.now().isoformat(), session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: str) -> bool:
    conn = _get_db()
    conn.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
    cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def add_session_message(session_id: str, role: str, content: str, options: Optional[str] = None):
    now = datetime.now().isoformat()
    conn = _get_db()
    conn.execute(
        "INSERT INTO session_messages (session_id, role, content, options, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, options, now),
    )
    conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    conn.close()


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM session_messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
