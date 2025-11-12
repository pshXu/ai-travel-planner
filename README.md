# AI 旅行规划师 Agent

一个可扩展的智能旅行规划系统，支持：
- 自然语言输入解析（目的地、天数、预算、同行人数与类型、偏好、特殊需求）
- 自动行程生成（交通、住宿、景点、餐饮、时间规划）
- 预算分配与三档建议（经济/舒适/豪华）
- 费用跟踪与超支预警

## 快速开始

1. 进入项目目录：
   - `cd ai-travel-planner`
2. 启动 Web 界面：
   - 安装依赖：`pip install -r requirements.txt`
   - 启动服务：`DEEPSEEK_API_KEY="你的密钥" - uvicorn web_app:app --reload --port 8000`
   - 打开：`http://127.0.0.1:8000/`


无需安装第三方依赖，示例基于标准库运行。

## 运行指南

- 配置（二选一）：
  - 编辑 `travel_planner_agent/config.py`，将 `DEEPSEEK_API_KEY` 填为你的密钥；可选调整 `DEEPSEEK_MODEL`、`DEEPSEEK_API_BASE`。
  - 或在终端设置环境变量：
    - `export DEEPSEEK_API_KEY="你的Key"`
    - 可选：`export DEEPSEEK_MODEL="deepseek-chat"`、`export DEEPSEEK_API_BASE="https://api.deepseek.com"`
    - 控制开关：`export LLM_PARSE=1`、`export LLM_PLAN=1`

- 安装依赖：
  - `pip install -r requirements.txt`

- 启动 Web 服务：
  - `uvicorn web_app:app --reload --port 8000`

## Supabase 部署指南

本项目支持使用 Supabase 托管用户认证（Auth）与 Postgres 数据库，并通过 RLS 实现数据的行级隔离。以下步骤可让你从零到上线。

### 1. 在 Supabase 创建项目并开启邮箱登录
- 前往 `https://supabase.com/` 创建新项目。
- 在 `Project Settings → API` 复制：
  - `Project URL`（作为 `SUPABASE_URL`）
  - `anon public`（作为 `SUPABASE_ANON_KEY`）
- 在 `Authentication → Providers → Email` 开启 Email 登录；可选择是否启用邮箱验证（开发阶段可关闭以降低流程复杂度）。

### 2. 创建 plans 表与 RLS 策略
- 打开 Supabase 的 `SQL Editor`，将本仓库中的 `supabase/plans.sql` 内容复制进去并执行。
- 该脚本会创建 `public.plans` 表并启用 RLS，策略为“仅允许用户访问自己的数据”。

SQL 脚本要点（策略片段，可复制）：
```
-- 仅允许用户访问自己的数据（Postgres 不支持 CREATE POLICY IF NOT EXISTS）
drop policy if exists "select own" on public.plans;
create policy "select own" on public.plans
  for select using (auth.uid() = user_id);

drop policy if exists "insert own" on public.plans;
create policy "insert own" on public.plans
  for insert with check (auth.uid() = user_id);

drop policy if exists "update own" on public.plans;
create policy "update own" on public.plans
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "delete own" on public.plans;
create policy "delete own" on public.plans
  for delete using (auth.uid() = user_id);
```


### 3. 在应用侧设置环境变量
运行 FastAPI 服务前，在环境中设置以下变量：
- `SUPABASE_URL`: Supabase 项目的 `Project URL`
- `SUPABASE_ANON_KEY`: Supabase 的 `anon public` key
- `SESSION_SECRET`: 任意随机字符串，用于会话加密（例如 `openssl rand -hex 32` 生成）

示例（macOS/zsh）：
```
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_ANON_KEY="eyJhbGciOi..."
export SESSION_SECRET=$(openssl rand -hex 32)
uvicorn web_app:app --reload --port 8000
```

也可以使用 `.env` 文件：
- 复制 `ai-travel-planner/.env.example` 为 `ai-travel-planner/.env`，填入你的项目值。
- 在终端执行：
  - `cd ai-travel-planner`
  - `source .env`
  - `uvicorn web_app:app --reload --port 8000`

注意：项目当前未内置自动加载 `.env` 的逻辑（未使用 `python-dotenv`），因此需要在终端通过 `source .env` 方式将变量写入当前会话，或在部署平台的环境配置处直接设置变量。

也支持像“大模型 API 与语音识别”一样通过 `travel_planner_agent/config.py` 配置：
- 在 `config.py` 中填入 `SUPABASE_URL` 与 `SUPABASE_ANON_KEY`，代码会优先读取这里的值；为空则回退到环境变量。
- 该方式适合本地开发，避免频繁在终端设置变量；请勿在公共仓库提交真实密钥。

### 4. 本地验证
- 打开 `http://127.0.0.1:8000/register` 使用邮箱+密码注册；若开启邮箱验证，需在邮箱点击确认后再登录。
- 登录后使用首页的表单生成旅行计划；点击“保存计划”，在“我的计划”查看列表、打开详情或删除。
- 当 `SUPABASE_URL` 与 `SUPABASE_ANON_KEY` 未设置时，应用会自动回退到 SQLite（`app.db`）。

### 5. 上线部署（示例：Render）
- 新建 Web Service，指向该项目。
- 配置环境变量：`SUPABASE_URL`、`SUPABASE_ANON_KEY`、`SESSION_SECRET`。
- 启动命令：`uvicorn web_app:app --host 0.0.0.0 --port $PORT`

其他平台（Fly.io / Railway / Docker 自托管）类似，关键是带上环境变量并使用 `uvicorn` 启动。

### 常见问题
- 开启邮箱验证时，未确认的账号无法登录；请检查 Supabase Auth 的邮件投递配置。
- 我们只使用 `anon` key + 用户会话配合 RLS，不需要 `SERVICE_ROLE_KEY`；避免在前端或公开环境暴露服务密钥。
- 高并发场景可考虑按请求使用会话令牌创建 Supabase 客户端，降低多用户共享客户端的风险。

  - 打开 `http://127.0.0.1:8000/`，填写表单并提交，即可生成结构化行程与预算；支持导出 JSON/CSV。

- 命令行模式：
  - `python main.py` 会在终端打印结果并生成 `output_trip.json` 与 `output_budget.csv`。

- 验证与故障排查：
  - 修改 `config.py` 或环境变量后，请重启服务使配置生效。
  - 若回退到静态结果或报未配置，请检查 Key 是否正确填写、变量是否在同一终端会话设置。
  - 可运行 `python -c 'import os; print(os.environ.get("DEEPSEEK_API_KEY"))'` 验证环境变量是否生效。

> 安全提示：`config.py` 仅用于本地开发，请勿将真实密钥提交至公共仓库。

## 项目结构

```
ai-travel-planner/
  README.md
  requirements.txt
  main.py
  travel_planner_agent/
    __init__.py
    parser.py
    planner.py
    budget.py
    expenses.py
    output.py
    tips.py
    providers.py
```

## 设计说明

- parser：解析中文自然语言，提取目的地、天数/日期、预算、人数与类型、偏好、特殊需求。
- planner：依据目的地与偏好生成每日详细行程，含交通/住宿/景点/餐饮与时间安排，避免不必要折返。
- budget：将总预算按比例分配到交通/住宿/餐饮/门票/其他，并给出经济/舒适/豪华三档建议与各项估算。
- expenses：费用数据结构与跟踪，支持分类记录实际支出、对比预算与超支预警。
- output：结构化输出（字典/文本），支持导出 JSON/CSV，便于保存与分享。
- tips：实用信息（天气、交通卡与优惠券、当地文化与注意事项）。
- providers：可对接实时信息源（景点/餐厅/票务等），示例中提供静态数据与接口约定。

### LLM（DeepSeek）集成
- 新增模块：`travel_planner_agent/llm.py`
- 可选本地配置：`travel_planner_agent/config.py`（推荐本地开发直接填入API Key）
- 环境变量：
  - `DEEPSEEK_API_KEY`：DeepSeek API Key（必填以启用）
  - `DEEPSEEK_MODEL`：模型名（默认 `deepseek-chat`）
  - `DEEPSEEK_API_BASE`：可选，默认 `https://api.deepseek.com`
  - `LLM_PARSE`：是否使用LLM解析（默认 `1` 开启）
  - `LLM_PLAN`：是否使用LLM生成行程（默认 `1` 开启）
- 安装依赖：`pip install openai`
- 生效逻辑：
  - 代码会优先读取 `travel_planner_agent/config.py` 中的配置；如为空则读取环境变量。
  - 当未配置或调用失败时，系统会直接在页面与接口返回“无法调用LLM”的错误提示，不再回退到静态结果。

### 语音输入（科大讯飞 ASR）
- 页面中的“旅行目的地”“多个城市”“补充信息”旁提供“语音输入”按钮，浏览器录音后上传 16k PCM WAV 到后端进行识别，结果自动填入对应输入框。
- 配置方式（二选一，优先读取配置文件，空则回退环境变量）：
  - 配置文件：`travel_planner_agent/config.py`
    - `XFYUN_APPID = "你的AppID"`
    - `XFYUN_API_KEY = "你的API Key"`
    - `XFYUN_API_SECRET = "你的API Secret"`
    - 修改后请重启后端服务使其生效。
  - 环境变量（macOS/zsh示例）：
    - `export XFYUN_APPID="你的AppID"`
    - `export XFYUN_API_KEY="你的API Key"`
    - `export XFYUN_API_SECRET="你的API Secret"`
    - 启动服务：`uvicorn web_app:app --reload --port 8000`
    - 验证变量：`python -c 'import os; print(os.environ.get("XFYUN_APPID"))'`
- 后端接口与格式：
  - 前端以 `audio/wav`（16k、单声道、PCM）上传至 `/api/asr`，请求体为 `multipart/form-data`，包含文件字段 `file` 以及目标填充字段 `field`（如 `destination`/`cities`/`extra_info`）。
  - 若你的后端尚未实现 `/api/asr`，请添加该接口并调用科大讯飞流式/HTTP识别 API；接口读取上述凭证进行签名认证，返回识别出的纯文本。
- 常见问题：
  - 浏览器需授权麦克风；推荐桌面版 Chrome/Edge。iOS Safari 对 `MediaRecorder`/WAV 编码支持有限，移动端建议提测。
  - 未配置或凭证错误时，识别接口会返回错误；请检查 `config.py` 或环境变量是否正确、服务是否重启。
  - 语音上传失败请检查网络、跨域、以及请求头的 `Content-Type` 是否为 `multipart/form-data`。

> 安全提示：请勿将真实讯飞密钥提交到公共仓库；本地开发可用 `config.py`，生产环境推荐使用环境变量与密钥管理。

## 示例输入

"我想去日本,5天,预算1万元,喜欢美食和动漫,带孩子"

## 注意与约束

- 推荐信息以真实可行为准；示例包含保守、通用的目的地与时间安排。接入实时信息源（`providers`）后可进一步精确。
- 预算分配留出应急空间，行程考虑体力与交通效率，优先满足明确偏好与特殊需求。
 - LLM生成内容会根据上下文变化，建议配合静态兜底与后置校验确保结构化输出一致。

