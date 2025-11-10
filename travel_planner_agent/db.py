import os
import sqlite3
import hashlib
import datetime
from typing import Optional, List, Dict

from .supabase_client import get_supabase_client


def _db_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_dir, "app.db")


def _use_supabase() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY"))


def init_db() -> None:
    if _use_supabase():
        # Supabase 使用托管 Postgres 与 Row Level Security；无需本地初始化
        return
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                data_json TEXT NOT NULL,
                params_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _hash_password(password: str, salt_hex: Optional[str] = None) -> (str, str):
    if salt_hex is None:
        salt = os.urandom(16)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex(), salt_hex


def create_user(username: str, password: str) -> Optional[str]:
    """Create user. Returns error message if failed, otherwise None.

    在 Supabase 模式下，username 作为 email 使用。
    """
    if _use_supabase():
        client = get_supabase_client()
        assert client is not None
        try:
            client.auth.sign_up({"email": username, "password": password})
            return None
        except Exception as e:
            return f"注册失败：{e}"
    # SQLite 回退
    conn = sqlite3.connect(_db_path())
    try:
        cur = conn.execute("SELECT id FROM users WHERE username=?", (username,))
        if cur.fetchone():
            return "用户名已存在"
        pwd_hash, salt_hex = _hash_password(password)
        now = datetime.datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO users(username, password_hash, password_salt, created_at) VALUES(?,?,?,?)",
            (username, pwd_hash, salt_hex, now),
        )
        conn.commit()
        return None
    finally:
        conn.close()


def verify_user(username: str, password: str) -> Optional[Dict]:
    if _use_supabase():
        client = get_supabase_client()
        assert client is not None
        try:
            res = client.auth.sign_in_with_password({"email": username, "password": password})
            user = res.user
            session = res.session
            if not user or not session:
                return None
            return {"id": user.id, "username": user.email, "access_token": session.access_token}
        except Exception:
            return None
    # SQLite 回退
    conn = sqlite3.connect(_db_path())
    try:
        cur = conn.execute(
            "SELECT id, username, password_hash, password_salt FROM users WHERE username=?",
            (username,),
        )
        row = cur.fetchone()
        if not row:
            return None
        user_id, uname, pwd_hash, pwd_salt = row
        candidate_hash, _ = _hash_password(password, pwd_salt)
        if candidate_hash == pwd_hash:
            return {"id": user_id, "username": uname}
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[Dict]:
    if _use_supabase():
        # 仅用于展示用户名，真实环境可使用 access_token 调用 gotrue /auth/v1/user
        return {"id": user_id}
    conn = sqlite3.connect(_db_path())
    try:
        cur = conn.execute("SELECT id, username FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "username": row[1]}
    finally:
        conn.close()


def create_plan(user_id: str, title: str, data_json: str, params_json: Optional[str]) -> str:
    if _use_supabase():
        client = get_supabase_client()
        assert client is not None
        res = client.table("plans").insert({
            "user_id": user_id,
            "title": title,
            "data_json": data_json,
            "params_json": params_json,
        }).execute()
        row = (res.data or [{}])[0]
        return str(row.get("id"))
    conn = sqlite3.connect(_db_path())
    try:
        now = datetime.datetime.utcnow().isoformat()
        cur = conn.execute(
            "INSERT INTO plans(user_id, title, data_json, params_json, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (user_id, title, data_json, params_json, now, now),
        )
        conn.commit()
        return str(cur.lastrowid)
    finally:
        conn.close()


def list_plans(user_id: str) -> List[Dict]:
    if _use_supabase():
        client = get_supabase_client()
        assert client is not None
        res = client.table("plans").select("id,title,created_at,updated_at").eq("user_id", user_id).order("updated_at", desc=True).execute()
        rows = res.data or []
        return rows
    conn = sqlite3.connect(_db_path())
    try:
        cur = conn.execute(
            "SELECT id, title, created_at, updated_at FROM plans WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
        return [
            {"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def get_plan(plan_id: str, user_id: str) -> Optional[Dict]:
    if _use_supabase():
        client = get_supabase_client()
        assert client is not None
        res = client.table("plans").select("id,title,data_json,params_json,created_at,updated_at").eq("id", plan_id).eq("user_id", user_id).limit(1).execute()
        rows = res.data or []
        return rows[0] if rows else None
    conn = sqlite3.connect(_db_path())
    try:
        cur = conn.execute(
            "SELECT id, title, data_json, params_json, created_at, updated_at FROM plans WHERE id=? AND user_id=?",
            (plan_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "data_json": row[2],
            "params_json": row[3],
            "created_at": row[4],
            "updated_at": row[5],
        }
    finally:
        conn.close()


def delete_plan(plan_id: str, user_id: str) -> bool:
    if _use_supabase():
        client = get_supabase_client()
        assert client is not None
        res = client.table("plans").delete().eq("id", plan_id).eq("user_id", user_id).execute()
        return (res.data is not None) and len(res.data) > 0
    conn = sqlite3.connect(_db_path())
    try:
        cur = conn.execute("DELETE FROM plans WHERE id=? AND user_id=?", (plan_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def update_user_password(user_id: str, new_password: str) -> bool:
    """Update user's password.

    - Supabase: uses auth.update_user with current session.
    - SQLite: updates hash and salt in users table.
    """
    if _use_supabase():
        client = get_supabase_client()
        assert client is not None
        try:
            client.auth.update_user({"password": new_password})
            return True
        except Exception:
            return False
    # SQLite fallback
    conn = sqlite3.connect(_db_path())
    try:
        new_hash, new_salt = _hash_password(new_password)
        cur = conn.execute(
            "UPDATE users SET password_hash=?, password_salt=? WHERE id=?",
            (new_hash, new_salt, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()