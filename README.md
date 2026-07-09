# weibo-checkin-selfhost

一个适合个人部署的微博超话自动签到工具。项目只做一件事：读取你自己的微博登录态，按计划完成已关注超话签到，并把结果通过 PushPlus 或邮箱推送给你。

## 功能

- 多微博账号签到，一行一个 Cookie
- 支持本地运行、Docker 自托管、GitHub Actions
- 支持扫码登录获取 Cookie
- 支持 PushPlus 和 SMTP 邮箱通知
- 默认每天 `06:00` 执行，可通过环境变量修改
- 不包含多用户网站、后台管理、数据库

## Docker 部署

复制环境变量示例：

```bash
cp .env.example .env
```

准备 Cookie 文件：

```bash
mkdir -p data
cp cookies.example.txt data/cookies.txt
```

编辑 `data/cookies.txt`，一行一个完整 Cookie：

```text
SUB=...; SUBP=...; SCF=...; ALF=...
SUB=...; SUBP=...; SCF=...; ALF=...
```

启动：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

默认每天 `06:00` 执行一次。修改 `.env`：

```env
RUN_AT=07:30
RUN_ON_START=true
```

`RUN_ON_START=true` 表示容器启动后先立即执行一次，之后再按计划运行。

## 本地运行

安装依赖：

```bash
uv sync
```

复制配置：

```bash
cp cookies.example.txt cookies.txt
```

执行签到：

```bash
uv run weibo-checkin --config cookies.txt
```

## 扫码登录获取 Cookie

本地安装登录依赖：

```bash
uv sync --extra login
uv run playwright install chromium
```

扫码登录并写入 `cookies.txt`：

```bash
uv run weibo-checkin login
```

追加多个微博账号：

```bash
uv run weibo-checkin login --append
```

说明：

- 扫码登录只保存 Cookie，不保存微博账号密码
- `cookies.txt`、`data/`、`logs/` 已被 `.gitignore` 忽略
- 如果签到出现 `382006 权限错误` 或 Cookie 失效，重新扫码刷新 Cookie

## 通知配置

PushPlus：

```env
PUSHPLUS_TOKEN=你的PushPlusToken
```

邮箱：

```env
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USERNAME=你的邮箱
SMTP_PASSWORD=邮箱授权码
SMTP_FROM=你的邮箱
SMTP_TO=接收通知的邮箱
SMTP_USE_TLS=true
```

## GitHub Actions

仓库自带 `.github/workflows/checkin.yml`。如果不想自己部署服务器，也可以在 GitHub Actions 里配置：

- `WEIBO_COOKIES`：一行一个完整 Cookie
- `PUSHPLUS_TOKEN`：可选
- `SMTP_*`：可选

默认 GitHub Actions 使用 UTC 时间 `22:00`，对应北京时间第二天 `06:00`。

## 维护建议

- 先连续观察 7 到 14 天，确认 Cookie 有效期和失败原因
- 失败后优先看日志里的错误码，例如 `382006`、`missing x-log-uid`
- 同一个账号不要过度频繁执行
- Cookie 属于敏感信息，不要上传到 GitHub
