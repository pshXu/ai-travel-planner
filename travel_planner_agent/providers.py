from typing import Dict, List
import os
import time
import json
import base64
import hashlib
import hmac
import asyncio
import ssl
import urllib.request
import urllib.parse
from email.utils import formatdate

from . import config


def static_attractions_tokyo() -> List[Dict]:
    # 票价以人民币近似（汇率约 1 JPY ≈ 0.05 CNY，仅供预算参考）
    return [
        {
            "name": "浅草寺",
            "type": "文化",
            "open_time": "06:00-17:00",
            "ticket_cny": 0,
            "duration_hours": 2,
            "suitable": ["成人", "亲子"],
            "area": "浅草",
        },
        {
            "name": "东京晴空塔",
            "type": "地标",
            "open_time": "10:00-21:00",
            "ticket_cny": 100,
            "duration_hours": 2,
            "suitable": ["成人", "亲子"],
            "area": "押上",
        },
        {
            "name": "秋叶原电器街",
            "type": "动漫",
            "open_time": "10:00-20:00",
            "ticket_cny": 0,
            "duration_hours": 3,
            "suitable": ["成人", "亲子"],
            "area": "秋叶原",
        },
        {
            "name": "台场海滨公园与商圈",
            "type": "购物",
            "open_time": "10:00-21:00",
            "ticket_cny": 0,
            "duration_hours": 3,
            "suitable": ["成人", "亲子"],
            "area": "台场",
        },
        {
            "name": "上野动物园",
            "type": "亲子",
            "open_time": "09:30-17:00(周一闭馆)",
            "ticket_cny": 30,
            "duration_hours": 3,
            "suitable": ["亲子"],
            "area": "上野",
        },
        {
            "name": "teamLab Planets",
            "type": "艺术",
            "open_time": "10:00-20:00(需预约)",
            "ticket_cny": 150,
            "duration_hours": 2,
            "suitable": ["成人", "亲子"],
            "area": "丰洲",
        },
        {
            "name": "明治神宫",
            "type": "文化",
            "open_time": "05:00-18:00(季节变化)",
            "ticket_cny": 0,
            "duration_hours": 1.5,
            "suitable": ["成人", "亲子"],
            "area": "原宿",
        },
        {
            "name": "涩谷十字路口与天空平台(免费)",
            "type": "地标",
            "open_time": "全天",
            "ticket_cny": 0,
            "duration_hours": 1.5,
            "suitable": ["成人", "亲子"],
            "area": "涩谷",
        },
    ]


def static_restaurants_tokyo() -> List[Dict]:
    return [
        {
            "name": "一兰拉面(各店)",
            "cuisine": "拉面",
            "avg_spend_cny": 80,
            "area": "多区域",
            "features": ["亲子友好", "动漫文化受众多"],
        },
        {
            "name": "牛かつ(牛排炸物)",
            "cuisine": "日式",
            "avg_spend_cny": 120,
            "area": "新宿/秋叶原等",
            "features": ["人气高", "排队较多"],
        },
        {
            "name": "筑地场外市场",
            "cuisine": "海鲜",
            "avg_spend_cny": 150,
            "area": "筑地",
            "features": ["新鲜食材", "适合美食爱好者"],
        },
    ]


def static_hotels_tokyo() -> List[Dict]:
    return [
        {
            "name": "浅草商务酒店(示例)",
            "area": "浅草",
            "price_range_cny": [450, 700],
            "features": ["交通便捷", "亲子友好", "房间较小"],
        },
        {
            "name": "上野家庭旅馆(示例)",
            "area": "上野",
            "price_range_cny": [500, 800],
            "features": ["适合亲子", "近公园"],
        },
        {
            "name": "新宿连锁酒店(示例)",
            "area": "新宿",
            "price_range_cny": [600, 900],
            "features": ["夜生活丰富", "餐饮选择多"],
        },
    ]


def static_transport_tokyo() -> Dict:
    return {
        "airport_city": [
            {"route": "成田 → 上野", "mode": "京成Skyliner", "cost_cny": 170, "duration_min": 41},
            {"route": "成田 → 东京站", "mode": "JR N'EX", "cost_cny": 200, "duration_min": 60},
        ],
        "local": [
            {"card": "Suica/ICOCA", "benefit": "城铁/地铁/公交通用，进出站快捷"},
            {"pass": "Tokyo Subway Ticket 48h", "cost_cny": 70, "benefit": "48小时地铁无限次"},
        ],
    }


def get_static_city_bundle(city: str) -> Dict:
    if city == "东京":
        return {
            "attractions": static_attractions_tokyo(),
            "restaurants": static_restaurants_tokyo(),
            "hotels": static_hotels_tokyo(),
            "transport": static_transport_tokyo(),
        }
    return {"attractions": [], "restaurants": [], "hotels": [], "transport": {}}


def transcribe_wav16_xfyun(wav_bytes: bytes) -> str:
    """
    使用科大讯飞 WebAPI（语音听写/iat）进行中文语音识别。
    期望输入为 16k 单声道 PCM WAV（前端已编码）。

    配置读取优先级：config.py -> 环境变量。
    环境变量：XFYUN_APPID / XFYUN_API_KEY / XFYUN_API_SECRET。
    返回识别出的纯文本；异常时抛出 RuntimeError。
    """
    appid = getattr(config, "XFYUN_APPID", None) or os.getenv("XFYUN_APPID")
    api_key = getattr(config, "XFYUN_API_KEY", None) or os.getenv("XFYUN_API_KEY")
    api_secret = getattr(config, "XFYUN_API_SECRET", None) or os.getenv("XFYUN_API_SECRET")
    if not (appid and api_key and api_secret):
        raise RuntimeError("讯飞ASR未配置：请在config.py或环境变量填写 XFYUN_APPID / XFYUN_API_KEY / XFYUN_API_SECRET")

    # WebAPI iat 接口
    url = "https://api.xfyun.cn/v1/service/v1/iat"

    # 参数：16k，原始PCM；不同账号可能需要调整 engine_type
    x_param = {
        "engine_type": "sms16k",
        "aue": "raw",
    }
    x_param_b64 = base64.b64encode(json.dumps(x_param, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    cur_time = str(int(time.time()))
    checksum_src = (api_key + cur_time + x_param_b64).encode("utf-8")
    x_checksum = hashlib.md5(checksum_src).hexdigest()

    audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
    post_data = urllib.parse.urlencode({"audio": audio_b64}).encode("utf-8")
    headers = {
        "X-Appid": appid,
        "X-CurTime": cur_time,
        "X-Param": x_param_b64,
        "X-CheckSum": x_checksum,
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    }

    req = urllib.request.Request(url, data=post_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"调用讯飞ASR失败：{e}")

    try:
        data = json.loads(body)
    except Exception:
        raise RuntimeError("讯飞ASR返回非JSON响应")

    code = data.get("code")
    if code != 0:
        desc = data.get("desc") or data.get("message") or "未知错误"
        raise RuntimeError(f"讯飞ASR错误：code={code}, desc={desc}")

    # 常见返回：{"code":0, "data":"识别文本"} 或 {"code":0, "data":{"result":"文本"}}
    result = data.get("data")
    if isinstance(result, dict):
        text = result.get("result") or result.get("text") or ""
    else:
        text = result or ""
    return (text or "").strip()


async def transcribe_wav16_xfyun_ws(wav_bytes: bytes) -> str:
    """
    使用科大讯飞 语音听写（流式版 WebSocket v2）进行中文语音识别。
    期望输入为 16k 单声道 PCM WAV（前端已编码）。

    认证与签名参照官方文档：
    - 连接地址：wss://iat-api.xfyun.cn/v2/iat
    - query 参数：authorization（Base64后的授权串）、date（RFC1123）、host
    - 授权串原文：api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"
    - signature 计算：HMAC-SHA256(api_secret, "host: {host}\ndate: {date}\nGET /v2/iat HTTP/1.1")，再 Base64

    为便于在 FastAPI 异步路由中使用，此函数为 async。
    如你的环境未安装 websockets 库，请安装后使用（pip install websockets）。
    """
    try:
        import websockets
    except Exception:
        raise RuntimeError("未找到 websockets 库：请安装依赖 pip install websockets 后再试")

    appid = getattr(config, "XFYUN_APPID", None) or os.getenv("XFYUN_APPID")
    api_key = getattr(config, "XFYUN_API_KEY", None) or os.getenv("XFYUN_API_KEY")
    api_secret = getattr(config, "XFYUN_API_SECRET", None) or os.getenv("XFYUN_API_SECRET")
    if not (appid and api_key and api_secret):
        raise RuntimeError("讯飞ASR未配置：请在config.py或环境变量填写 XFYUN_APPID / XFYUN_API_KEY / XFYUN_API_SECRET")

    host = "iat-api.xfyun.cn"
    path = "/v2/iat"
    date = formatdate(timeval=None, localtime=False, usegmt=True)

    # 生成签名
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = hmac.new(api_secret.encode("utf-8"), signature_origin.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

    query = urllib.parse.urlencode({
        "authorization": authorization,
        "date": date,
        "host": host,
    })
    ws_url = f"wss://{host}{path}?{query}"

    # 从 WAV 中提取裸PCM（本项目前端生成固定44字节头）
    if len(wav_bytes) < 44:
        raise RuntimeError("上传的音频数据无效：WAV长度不足")
    pcm = wav_bytes[44:]

    # 组帧并发送
    ssl_ctx = ssl.create_default_context()
    result_text_parts: List[str] = []

    async with websockets.connect(ws_url, ssl=ssl_ctx) as ws:
        # 首包：status=0
        def make_frame(chunk: bytes, status: int) -> str:
            data_b64 = base64.b64encode(chunk).decode("utf-8")
            frame = {
                "common": {"app_id": appid},
                "business": {
                    "language": "zh_cn",
                    "domain": "iat",
                    "accent": "mandarin",
                    "vad_eos": 1000,
                    "ptt": 1,
                },
                # 注意：顶层是 data，而不是 audio；字段名为 format/encoding/status/audio
                "data": {
                    "format": "audio/L16;rate=16000",
                    "encoding": "raw",
                    "status": status,
                    "audio": data_b64,
                },
            }
            return json.dumps(frame, ensure_ascii=False)

        # 官方示例建议 1280 字节一帧（约40ms）
        chunk_size = 1280
        offset = 0

        # 发送首帧
        first = pcm[offset:offset + chunk_size]
        await ws.send(make_frame(first, 0))
        offset += len(first)

        # 循环发送中间帧
        while offset < len(pcm):
            end = min(offset + chunk_size, len(pcm))
            status = 1 if end < len(pcm) else 2
            await ws.send(make_frame(pcm[offset:end], status))
            offset = end
            # 适当让出事件循环，以便及时接收服务端结果
            await asyncio.sleep(0.02)

        # 接收识别结果，直到服务端主动关闭或超时
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(msg)
                if data.get("code") != 0:
                    desc = data.get("message") or data.get("desc") or "未知错误"
                    raise RuntimeError(f"讯飞ASR错误：code={data.get('code')}, desc={desc}")
                result = (((data.get("data") or {}).get("result") or {}))
                # 解析 ws/cw 结构
                ws_list = result.get("ws") or []
                for ws_item in ws_list:
                    cw_list = ws_item.get("cw") or []
                    for cw in cw_list:
                        w = cw.get("w")
                        if w:
                            result_text_parts.append(w)
        except asyncio.TimeoutError:
            # 超时视为流结束
            pass
        except websockets.exceptions.ConnectionClosed:
            pass

    text = "".join(result_text_parts).strip()
    return text