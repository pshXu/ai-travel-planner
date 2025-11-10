"""
本地配置文件（可选）：你可以直接在这里填入 API Key 等配置。
代码会优先读取此文件中的值；如果为空，则回退到环境变量。

注意：此文件仅用于本地开发，请勿提交到公共仓库。
"""

# 必填：你的 API Key（字符串），例如："sk-xxxx"
DEEPSEEK_API_KEY = "sk-uWbzwH52XMIZabjoaVyMFvyE5i56dkSSnEug17RoDHdN243I"

# 可选：模型名与API地址
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_API_BASE = "https://api.openai-proxy.org/v1"

# 语音识别（科大讯飞）本地开发配置：
# 若留空，将回退到环境变量 XFYUN_APPID / XFYUN_API_KEY / XFYUN_API_SECRET
XFYUN_APPID = "532557ca"
XFYUN_API_KEY = "03647435cbba2d4228d10dc3e584f813"
XFYUN_API_SECRET = "MzQwNDA2NjY4ZDcxZDEwZjBmZjJlZWQx"

# Supabase（可选）：若留空，将回退到环境变量 SUPABASE_URL / SUPABASE_ANON_KEY
SUPABASE_URL = "https://knophzrgpzyuxkuzqnxd.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtub3BoenJncHp5dXhrdXpxbnhkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE3MjE3MjEsImV4cCI6MjA3NzI5NzcyMX0.w5cLiglkwXjiqB-evaV7hmYPyiYPbK8BKHvn6w5chFM"

# 高德地图 Web JS API Key（前端加载 SDK 使用）：
# 若留空，将回退到环境变量 AMAP_WEB_KEY
AMAP_WEB_KEY = "2da26b9ae9cdf90dc4d1e2c9be70aa04"

# 高德地图 Web JS 安全密钥（securityJsCode）：用于前端 SDK 安全校验
# 若留空，将回退到环境变量 AMAP_SECURITY_JS_CODE
AMAP_SECURITY_JS_CODE = "5e0f98c310427e21e4036886bc32c76b"
