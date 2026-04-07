# weibo-auto-signin

一个尽量简单的微博超话自动签到工具，支持本地运行，也支持通过 GitHub Actions 定时执行。

项目默认思路只有一件事：你提供整串微博 Cookie，程序自动读取关注的超话并尝试完成当天签到。

English version: [docs/README.en.md](docs/README.en.md)

## 功能

- 支持一行一个 Cookie，多账号批量签到
- 支持直接粘贴整串微博 Cookie
- 支持本地命令行运行
- 支持 GitHub Actions 手动触发和定时触发
- 支持运行结束后发送汇总通知
- 支持 `PushPlus` 和通用 `SMTP` 邮件通知

## 不做什么

- 不负责帮你获取微博 Cookie
- 不保证能绕过 Cookie 失效、平台风控或接口变更
- 不在仓库测试里执行真实联网签到

## 环境要求

- Python `3.13`
- `uv`

## 本地使用

1. 克隆仓库。
2. 安装依赖。
3. 复制示例配置文件。
4. 把你自己的 Cookie 填进去。
5. 执行签到命令。

安装依赖：

```bash
uv sync
```

复制示例配置：

```bash
cp cookies.example.txt cookies.txt
```

运行命令：

```bash
uv run python -m weibo_auto_signin.cli --config cookies.txt
```

## Cookie 格式

`cookies.txt` 是纯文本文件，一行一个完整 Cookie：

```text
SUB=...; SUBP=...; SCF=...; ALF=...
SUB=...; SUBP=...; SCF=...; ALF=...
```

说明：

- 一行代表一个微博账号
- 空行会被自动忽略
- 建议直接从浏览器复制完整 Cookie，不要手动拆字段
- 程序当前强制要求 Cookie 中至少包含 `SUB` 和 `SUBP`
- 其他字段可以一起保留，例如 `XSRF-TOKEN`、`SCF`、`ALF`、`WBPSESS`
- 不要把真实 Cookie 提交到 Git 仓库

像下面这种更完整的 Cookie，也可以直接使用：

```text
XSRF-TOKEN=...; SCF=...; SUB=...; SUBP=...; ALF=...; WBPSESS=...
```

## 如何获取 Cookie

下面以 Chrome 和 Edge 为例，其他 Chromium 浏览器操作基本类似。

### 方法一：从开发者工具的 Network 里复制

这是最推荐的方式，复制到的内容通常最完整。

1. 先在浏览器里登录微博。
2. 打开 [weibo.com](https://weibo.com/) 并保持登录状态。
3. 按 `F12` 打开开发者工具。
4. 切换到 `Network` 面板。
5. 刷新当前页面。
6. 随便点开一个请求，在请求头里找到 `Cookie`。
7. 复制整串 `Cookie` 值。

注意：

- 只复制 `Cookie:` 后面的内容，不要把 `Cookie:` 这个前缀也带进去
- 复制后粘贴成一整行，不要换行
- 你拿到的内容可能比示例多很多字段，这没关系，直接整串使用即可

### 方法二：从 Application 里查看 Cookie

如果你不习惯看请求头，也可以这样拿：

1. 登录微博网页。
2. 按 `F12` 打开开发者工具。
3. 打开 `Application` 面板。
4. 左侧找到 `Storage` -> `Cookies` -> `https://weibo.com`
5. 找到对应的 Cookie 项。
6. 自己拼接成 `key=value; key=value` 这种格式。

这个方式也能用，但因为要手动拼接，不如方法一省事。

### 写入本地文件

把复制到的整串 Cookie 直接写到 `cookies.txt`，一行一个账号：

```text
XSRF-TOKEN=...; SCF=...; SUB=...; SUBP=...; ALF=...; WBPSESS=...
XSRF-TOKEN=...; SCF=...; SUB=...; SUBP=...; ALF=...; WBPSESS=...
```

### 写入 GitHub Actions Secret

如果你用 GitHub Actions，就把同样的内容填到 `WEIBO_COOKIES` 这个 Secret 里：

- 单账号就填一行
- 多账号就一行一个 Cookie
- 不要额外加引号
- 不要提交真实 Cookie 到仓库文件里

## GitHub Actions 配置

仓库已经自带 workflow 文件 [checkin.yml](.github/workflows/checkin.yml)，你只需要配置 Secrets 就可以运行。

### 第一步：Fork 或使用你自己的仓库

如果你是直接使用自己的仓库，跳过这一步。  
如果你是参考本项目，先 Fork 一份到自己的 GitHub 账号下。

### 第二步：添加签到 Cookie

打开仓库页面后，按下面路径进入：

`Settings` -> `Secrets and variables` -> `Actions`

点击 `New repository secret`，新增一个 Secret：

- 名称：`WEIBO_COOKIES`
- 内容：一行一个完整 Cookie

示例：

```text
SUB=...; SUBP=...; SCF=...; ALF=...
SUB=...; SUBP=...; SCF=...; ALF=...
```

如果你只有一个账号，就只填一行。

### 第三步：手动触发 workflow

打开仓库的 `Actions` 页面：

1. 选择 `Weibo Check-in`
2. 点击 `Run workflow`
3. 选择分支 `main`
4. 点击绿色按钮开始执行

执行结束后，可以在 Actions 日志里查看签到结果。

### 第四步：等待定时执行

当前仓库默认的定时任务是：

- `22:30 UTC`
- 对应中国时间 `06:30`

如果你想改执行时间，可以编辑 [checkin.yml](.github/workflows/checkin.yml) 里的 `cron` 表达式。

## 通知配置

通知不是必须项。  
如果你不配置通知，程序也会正常签到，只是结果只会出现在控制台和 GitHub Actions 日志里。

### 方案一：PushPlus 微信通知

如果你想在微信里收到运行汇总，在仓库 Secrets 里新增：

- `PUSHPLUS_TOKEN`

配置完成后，每次签到结束都会发送一条纯文本汇总。

#### 如何获取 PushPlus Token

1. 打开 [PushPlus 官网](https://www.pushplus.plus/)。
2. 使用微信登录。
3. 进入一对一消息页面或个人中心。
4. 找到你的 `用户 token`，也可以按需要新建 `消息 token`。
5. 复制 token 内容。

说明：

- 当前 PushPlus 官方页面支持直接查看 `用户 token`
- `用户 token` 和 `消息 token` 都可以用于发送消息
- 为了方便管理不同项目，推荐你单独创建一个 `消息 token` 给这个仓库使用
- PushPlus 官方目前要求完成实名认证后才能正常调用发送消息接口

#### 如何在 GitHub Actions 里配置 PushPlus

1. 打开仓库的 `Settings`
2. 进入 `Secrets and variables` -> `Actions`
3. 点击 `New repository secret`
4. 名称填写 `PUSHPLUS_TOKEN`
5. 值填写你刚刚复制的 token
6. 保存后重新运行 `Weibo Check-in` workflow

#### 如何在本地配置 PushPlus

本地运行时可以直接设置环境变量：

```bash
export PUSHPLUS_TOKEN="你的 pushplus token"
uv run python -m weibo_auto_signin.cli --config cookies.txt
```

如果配置正确，每次签到结束后都会收到一条微信通知。

### 方案二：SMTP 邮件通知

如果你想通过邮箱接收通知，在仓库 Secrets 里新增：

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_TO`

可选项：

- `SMTP_USE_TLS`
- `NOTIFY_TITLE_PREFIX`

说明：

- `SMTP_TO` 可以填写接收通知的邮箱地址
- `SMTP_USE_TLS=false` 表示关闭 STARTTLS
- `NOTIFY_TITLE_PREFIX` 可以自定义通知标题前缀

## GitHub Actions 需要配置哪些 Secret

最少只需要这一个：

- `WEIBO_COOKIES`

如果你还想开启通知，可以额外配置：

- `PUSHPLUS_TOKEN`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_TO`
- `SMTP_USE_TLS`
- `NOTIFY_TITLE_PREFIX`

## 常见问题

### 1. 运行失败，提示 Cookie 无效

通常说明：

- Cookie 过期了
- Cookie 内容不完整
- 微博登录状态已经失效

建议重新从浏览器复制最新 Cookie。

### 2. GitHub Actions 里运行失败

优先检查：

- `WEIBO_COOKIES` 是否已添加
- Cookie 是否是一行一个账号
- Secret 里有没有多余引号
- GitHub Actions 是否已启用

### 3. 本地可以跑，Actions 不稳定

这种情况通常和平台风控、Cookie 新旧程度、运行时间点有关。  
可以先更新 Cookie，再调整 workflow 执行时间。

## 开发

项目使用 `uv` 管理依赖。

运行测试：

```bash
uv run pytest
```

## 注意事项

- 自动签到存在账号风险，请自行评估后使用
- 微博接口随时可能变化，失效时请优先检查 Cookie 和平台接口变化
- 日志里不应该输出完整 Cookie，请不要把真实 Cookie 发给别人
