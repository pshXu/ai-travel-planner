import os
from typing import Optional

try:
    from supabase import create_client, Client
except Exception:
    Client = object  # type: ignore

try:
    from . import config as _cfg
except Exception:
    _cfg = None


def _cfg_get(name: str, default=None):
    # 优先读取本地配置文件；为空则回退到环境变量
    if _cfg and hasattr(_cfg, name):
        val = getattr(_cfg, name)
        if isinstance(val, str):
            if val.strip():
                return val.strip()
        elif val is not None:
            return val
    return os.environ.get(name, default)


_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    global _client
    url = _cfg_get("SUPABASE_URL")
    key = _cfg_get("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    if _client is None:
        _client = create_client(url, key)
    return _client