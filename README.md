<p align="right"><sub>Lang: <b>中文</b> | <a href="README.en.md">English</a></sub></p>

# 🎨 Hermes × MiniMax 生图小插件

<sub>Built with [Hermes Agent](https://hermes-agent.nousresearch.com/) in collaboration with the user.</sub>

> 一个 vibe coding 出来的玩意儿——**Hermes Agent**(那个会写代码、跑命令、记你偏好的 AI 助手)和**MiniMax** 联手,在 `image_generate` 工具里把 MiniMax 的 `image-01` / `image-01-live` 生图模型接了进来。
>
> 一行命令装好,Token Plan 用户的 `minimax-cn` chat key **自动复用**,不用单独配。生图配额跟文字共享,月底见。

- 仓库:[github.com/Upstream17/hermes-minimax-image-plugin](https://github.com/Upstream17/hermes-minimax-image-plugin)
- 协作者:Hermes Agent × MiniMax
- 风格:纯 vibe,不卷 — `plugin/__init__.py` 一个文件,装上就跑,跑不起来就报错,不会偷偷 fallback

## 为什么需要这个

Hermes 自带的生图 provider 有 `fal / krea / openai / openai-codex / openrouter / xai` —— **没有 MiniMax**。我们(MiniMax)想进 Hermes 的 `image_generate` 工具,但又不想动核心代码。Hermes 给的官方扩展姿势就是 user plugin,所以这个小仓库就出现了。

整个过程没 fork、没 PR、没改一行 hermes-agent 源码。

## 能干啥

- ✏️ **文生图(T2I)**:`image-01`(通用)和 `image-01-live`(更偏手绘/卡通)两个模型
- 🖌️ **图生图(I2I)**:用 `image-01` 给单张源图做编辑
- 📐 三种画幅:`landscape` (16:9) / `square` (1:1) / `portrait` (9:16)
- 🔗 返回的是签名 OSS URL(~24h 有效),如果想存本地自己拉一下

## 前置条件

- Hermes Agent **0.17.0+**(用到了 0.17 "The Reach Release" 引入的 user-plugin loader)
- 一个 **MiniMax Token Plan** 的 API key,到 [platform.minimax.io/user-center/payment/token-plan](https://platform.minimax.io/user-center/payment/token-plan) 拿。`minimax-cn` chat provider 用的是同一个 key
- Python 3.10+(hermes-agent 自己要求啥就啥)

## 一行命令装上

**macOS / Linux / WSL:**
```bash
curl -fsSL https://raw.githubusercontent.com/Upstream17/hermes-minimax-image-plugin/main/install.sh | bash
```

**Windows(PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Upstream17/hermes-minimax-image-plugin/main/install.ps1 | iex
```

装的时候脚本会做这些事:

1. 找到正确的 plugin 目录(Windows 在 `%LOCALAPPDATA%\hermes\plugins\image_gen\minimax\`,macOS/Linux/WSL 在 `~/.hermes/plugins/image_gen/minimax/` —— 这是 `hermes plugins install` 和 loader 都认的官方路径)
2. 把 `__init__.py` 和 `plugin.yaml` 复制进去
3. 跑 `hermes plugins enable minimax`(官方命令,顺便避开老版本 `hermes config set` 把 list 写成 string 的坑)
4. 跑 `hermes config set image_gen.provider minimax` 把生图路由切过来
5. **完全不碰** 你的 key——见下一节的自动检测规则

### 不想 curl pipe?手动装

```bash
# 1. 克隆
git clone https://github.com/Upstream17/hermes-minimax-image-plugin.git
cd hermes-minimax-image-plugin

# 2. 把 plugin 文件丢到 loader 扫描的目录
#    macOS / Linux / WSL:
mkdir -p ~/.hermes/plugins/image_gen/minimax
cp plugin/* ~/.hermes/plugins/image_gen/minimax/

#    Windows(PowerShell):
#    New-Item -ItemType Directory -Force -Path "$env:LOCALAPPDATA\hermes\plugins\image_gen\minimax"
#    Copy-Item plugin\* "$env:LOCALAPPDATA\hermes\plugins\image_gen\minimax\"

# 3. 启用
hermes plugins enable minimax

# 4. 切到 minimax 生图
hermes config set image_gen.provider minimax
```

`image_gen.model` 这一项**不设也行**,默认就是 `image-01`。想用 `image-01-live`:

```bash
hermes config set image_gen.model image-01-live
```

## 🔑 Key 自动检测 — 大概率你啥也不用做

plugin 会按顺序找 4 个地方,谁先有 key 就用谁:

1. `MINIMAX_CN_API_KEY` 环境变量
2. `MINIMAX_API_KEY` 环境变量(只有 global key 时的兜底)
3. `config.yaml` 里 `providers.minimax-cn.api_key` —— **如果你已经配过 `minimax-cn` chat provider,这里就有 key,生图直接用,不用再配一遍**
4. `$HERMES_HOME/.env` 里的 `MINIMAX_CN_API_KEY=...`

4 个地方都没,生图工具会回个 `auth_required` 错误,告诉你设哪个变量。要手动设:

```bash
# macOS / Linux / WSL
echo 'MINIMAX_CN_API_KEY=eyJhbGc...' >> ~/.hermes/.env

# Windows(PowerShell)
Add-Content "$env:LOCALAPPDATA\hermes\.env" 'MINIMAX_CN_API_KEY=eyJhbGc...'
```

> ⚠️ Token Plan 是**文图共享**一个 quota。生图多了月底文字额度会少,心里有数。

## 🌍 中国 / 全球 endpoint 切换

plugin 默认走 **中国 region endpoint**(`https://api.minimaxi.com/v1/image_generation`)。如果你的 key 是**国际版**(非中国 Token Plan 或 pay-as-you-go),设环境变量切到全球 endpoint:

```bash
# macOS / Linux / WSL
echo 'MINIMAX_IMAGE_API_URL=https://api.minimax.io/v1/image_generation' >> ~/.hermes/.env

# Windows(PowerShell)
Add-Content "$env:LOCALAPPDATA\hermes\.env" 'MINIMAX_IMAGE_API_URL=https://api.minimax.io/v1/image_generation'
```

> ⚠️ **诚实声明**:本作者**只有中国 region 账号**,国际 endpoint 是按 [MiniMax 官方文档](https://platform.minimax.io/docs/guides/image-generation) 写的,**未实测**。如果你在国际版上遇到怪问题(比如 model id 不一样、response 字段名不同),**先查官方文档**——plugin 的 response parser 是按中国 region 的 `data.image_urls` 形态写的。

## 装完怎么验证

```bash
# 1. loader 应该喊一嗓子
HERMES_PLUGINS_DEBUG=1 hermes chat -q "ping" --yolo -Q 2>&1 | grep minimax
# 应该看到:[plugins] INFO Plugin 'minimax' registered image_gen provider: minimax

# 2. 真生一张图
hermes chat -q "Generate an image: a small red apple on a white background" --yolo -Q
# 应该回一个 https://hailuo-image-algeng-data.oss-cn-wulanchabu.aliyuncs.com/.../aigc.jpeg 这样的 URL
```

## 不想用了

切回别的生图后端:

```bash
hermes config set image_gen.provider fal    # 或者 xai / openai / krea / openai-codex / openrouter
hermes config set image_gen.model fal-ai/flux-2/klein/9b
```

plugin 文件还在,只是不活跃。要彻底拔掉:

```bash
# 最省事:
hermes plugins uninstall minimax

# 或者手搓:
rm -rf ~/.hermes/plugins/image_gen/minimax       # macOS / Linux / WSL
Remove-Item -Recurse "$env:LOCALAPPDATA\hermes\plugins\image_gen\minimax"  # Windows
```

`config.yaml` 里 `plugins.enabled` 那一项也会被 `hermes plugins uninstall` 清掉,不用自己改。

## 模型一览

| Model id          | 风格                              | 文生图 | 图生图 |
|-------------------|-----------------------------------|:------:|:------:|
| `image-01`        | 通用,细节强                      |   ✅   |   ✅   |
| `image-01-live`   | 手绘/卡通味更重                   |   ✅   |   ❌   |

默认 `image-01`。换 `image-01-live` 用:
```bash
hermes config set image_gen.model image-01-live
```

## 仓库里都有啥

```
.
├── README.md              # English(主,国际用户看)
├── README.en.md        # 本文件(中文,默认显示给国内用户)
├── LICENSE                # MIT
├── CHANGELOG.md           # 版本日志
├── install.sh             # macOS / Linux / WSL 一键装
├── install.ps1            # Windows 一键装
├── fix-config-list.py     # 备用:老版本 Hermes <0.18 的 list 写成 string 的坑的修法(用 installer 就不用管这个)
└── plugin/
    ├── __init__.py        # 真正的 provider 代码,就这一个文件
    └── plugin.yaml        # 清单(name / kind / requires_env)
```

`plugin/` 目录就是装的东西。`__init__.py` 和 `plugin.yaml` 原样拷到 Hermes plugin 目录就行。

## 它怎么跑起来的(给好奇的人看)

`agent/image_gen_provider.py` 是 Hermes 的 `ImageGenProvider` ABC。Fal、xAI、OpenAI 这些后端都实现这个接口。这个 plugin 加了一个新实现,打的是 MiniMax 的 `/v1/image_generation` endpoint,带 Bearer token。

plugin 在 Hermes 启动时通过标准的 `register(ctx)` 入口挂上,写到 `agent/image_gen_registry.py` 的注册表里。`config.yaml` 里 `image_gen.provider = minimax` 就会路由过来。

完整契约见 [Hermes 官方文档](https://hermes-agent.nousresearch.com/docs/developer-guide/image-gen-provider-plugin)。

## 几个不大不小但你迟早会撞的坑

- 🕐 **返回的图 URL 是签名 OSS 链接,大约 24h 失效**。`Expires` 那个 query 参数就是。要长期存,自己下载到本地
- 💰 **Token Plan 共享配额**,生图吃文字预算,见上面
- 🤥 **MiniMax 官方文档写错了 response 格式**——它说字段是顶层的 `image_urls`,实际上是 `data.image_urls`。plugin 的 parser 写的是**真实**形态(基于中国 region 实测)
- 🌐 **国际 endpoint 未实测**:见上面"中国 / 全球 endpoint 切换"段

## 装不上?报错?看这里

**没看到 `Plugin 'minimax' registered image_gen provider: minimax`**

1. `hermes --version` ≥ 0.17
2. 文件确实在 `~/.hermes/plugins/image_gen/minimax/`(注意中间有 `image_gen/` 这一层,不是 `plugins/minimax/` —— 后者 loader 看不见)
3. `config.yaml` 里 `plugins.enabled` 真有 `minimax`:
   ```yaml
   plugins:
     enabled:
       - minimax
   ```
   如果写成了字符串(`enabled: '["minimax"]'`),跑一下 `python fix-config-list.py`(idempotent,老版本 Hermes <0.18 才需要)

**`MiniMax API key not found`** — 4 个自动检测源都没匹配上。要么 set 环境变量,要么跑 `hermes model` 把 `minimax-cn` chat provider 配上(那个 key plugin 也会用)。

**`MiniMax returned error: ...` 带 HTTP 401/403** — key 设了但不对当前 endpoint 域。
- 中国 endpoint(`api.minimaxi.com`)报 401 → key 可能是 global 的,设 `MINIMAX_IMAGE_API_URL=https://api.minimax.io/v1/image_generation` 切过去
- 全球 endpoint(`api.minimax.io`)报 401 → key 可能是中国的,清掉 `MINIMAX_IMAGE_API_URL` 走默认

## 🤝 贡献

Issues 和 PR 都欢迎。plugin 就一个文件,想 fork 改别的 MiniMax endpoint 或别的模型都轻轻松松。

## 📜 协议

MIT — 看 [LICENSE](LICENSE)。
