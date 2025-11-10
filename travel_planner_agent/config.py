"""
本地配置文件（可选）：你可以直接在这里填入 API Key 等配置。
代码会优先读取此文件中的值；如果为空，则回退到环境变量。

注意：此文件仅用于本地开发，请勿提交到公共仓库。
"""

# 必填：你的 API Key（字符串），例如："sk-xxxx"
DEEPSEEK_API_KEY = ""

# 可选：模型名与API地址
DEEPSEEK_MODEL = ""
DEEPSEEK_API_BASE = ""

# 语音识别（科大讯飞）本地开发配置：
# 若留空，将回退到环境变量 XFYUN_APPID / XFYUN_API_KEY / XFYUN_API_SECRET
XFYUN_APPID = ""
XFYUN_API_KEY = ""
XFYUN_API_SECRET = ""

# Supabase（可选）：若留空，将回退到环境变量 SUPABASE_URL / SUPABASE_ANON_KEY
SUPABASE_URL = ""
SUPABASE_ANON_KEY = ""

# 高德地图 Web JS API Key（前端加载 SDK 使用）：
# 若留空，将回退到环境变量 AMAP_WEB_KEY
AMAP_WEB_KEY = ""

# 高德地图 Web JS 安全密钥（securityJsCode）：用于前端 SDK 安全校验
# 若留空，将回退到环境变量 AMAP_SECURITY_JS_CODE
AMAP_SECURITY_JS_CODE = ""
