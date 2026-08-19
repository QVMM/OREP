"""MySQL access for PPT agent job queue (reuses orep database)."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger(__name__)

_pymysql = None


def _load_pymysql():
    global _pymysql
    if _pymysql is None:
        import pymysql

        _pymysql = pymysql
    return _pymysql


def db_enabled() -> bool:
    """True when MYSQL_* is configured (or SPRING-style fallbacks)."""
    if os.getenv("PPT_DB_DISABLED", "").lower() in {"1", "true", "yes", "on"}:
        return False
    host = (
        os.getenv("PPT_MYSQL_HOST")
        or os.getenv("MYSQL_HOST")
        or os.getenv("SPRING_DATASOURCE_HOST")
        or ""
    ).strip()
    password = (
        os.getenv("PPT_MYSQL_PASSWORD")
        or os.getenv("MYSQL_PASSWORD")
        or os.getenv("MYSQL_ROOT_PASSWORD")
        or os.getenv("SPRING_DATASOURCE_PASSWORD")
        or ""
    )
    # Allow empty password only if explicitly enabled (local dev).
    if not host:
        return False
    if not password and os.getenv("PPT_MYSQL_ALLOW_EMPTY_PASSWORD", "").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        # Still enable if user is set and host is mysql in docker (root password usually set)
        if not (os.getenv("PPT_MYSQL_USER") or os.getenv("MYSQL_USER") or os.getenv("MYSQL_ROOT_PASSWORD")):
            return False
    return True


def _conn_kwargs() -> dict[str, Any]:
    host = (
        os.getenv("PPT_MYSQL_HOST")
        or os.getenv("MYSQL_HOST")
        or "mysql"
    ).strip()
    port = int(os.getenv("PPT_MYSQL_PORT") or os.getenv("MYSQL_PORT") or "3306")
    user = (
        os.getenv("PPT_MYSQL_USER")
        or os.getenv("MYSQL_USER")
        or "root"
    ).strip()
    password = (
        os.getenv("PPT_MYSQL_PASSWORD")
        or os.getenv("MYSQL_PASSWORD")
        or os.getenv("MYSQL_ROOT_PASSWORD")
        or ""
    )
    database = (
        os.getenv("PPT_MYSQL_DATABASE")
        or os.getenv("MYSQL_DATABASE")
        or "orep"
    ).strip()
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "charset": "utf8mb4",
        "cursorclass": _load_pymysql().cursors.DictCursor,
        "autocommit": False,
        "connect_timeout": 5,
        "read_timeout": 30,
        "write_timeout": 30,
    }


@contextmanager
def get_connection() -> Iterator[Any]:
    if not db_enabled():
        raise RuntimeError("PPT MySQL is not configured")
    pymysql = _load_pymysql()
    conn = pymysql.connect(**_conn_kwargs())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping() -> bool:
    if not db_enabled():
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception as exc:
        logger.warning("PPT MySQL ping failed: %s", exc)
        return False
