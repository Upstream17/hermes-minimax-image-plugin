<p align="right"><sub>Lang: <a href="README.md">中文</a> | <b>English</b></sub></p>

# Hermes MiniMax Image Plugin

> A vibe-coded drop-in: Hermes Agent + MiniMax, exposing MiniMax's
> `image-01` and `image-01-live` models through Hermes's
> `image_generate` tool.
>
> One-line install. If you're on a Token Plan and have the
> `minimax-cn` chat provider configured, the same key is reused
> automatically — no extra setup.

This is the official extension path documented at
[`hermes-agent.nousresearch.com/docs/developer-guide/image-gen-provider-plugin`](https://hermes-agent.nousresearch.com/docs/developer-guide/image-gen-provider-plugin) —
zero source changes to `hermes-agent`, no PR, no fork.

> **Why a plugin?** Hermes's bundled image providers are `fal`, `krea`,
> `openai`, `openai-codex`, `openrouter`, and `xai`. MiniMax is not bundled.
> This plugin fills the gap without touching core.

## What you get

- **Text-to-image** (T2I) via `image-01` and `image-01-live`
- **Image-to-image / editing** (I2I) via `image-01` (single source image)
- 3 aspect ratios: `landscape` (16:9), `square` (1:1), `portrait` (9:16)
- Returns the image URL from MiniMax (signed Aliyun OSS, valid ~24h)
- Visible in the `hermes tools` picker alongside the bundled providers

## Endpoints — China (default) and Global

The plugin defaults to the **China-region endpoint**
(`https://api.minimaxi.com/v1/image_generation`). For users on a
**non-China Token Plan or pay-as-you-go key**, the global endpoint
(`https://api.minimax.io/v1/image_generation`) is supported per
[MiniMax's docs](https://platform.minimax.io/docs/guides/image-generation).
To switch:

```bash
# macOS / Linux / WSL
echo 'MINIMAX_IMAGE_API_URL=https://api.minimax.io/v1/image_generation' >> ~/.hermes/.env

# Windows (PowerShell)
Add-Content "$env:LOCALAPPDATA\hermes\.env" 'MINIMAX_IMAGE_API_URL=https://api.minimax.io/v1/image_generation'
```

> ⚠️ **Honest caveat.** The author only has a China-region account.
> The **China endpoint is verified end-to-end** (派蒙 + 苹果测试都跑过);
> the **global endpoint is documented but untested**. If you hit an
> issue on the global endpoint (model id mismatch, response shape
> change, key type), check the official docs first — the response
> parser in this plugin was written against the China response shape
> (`data.image_urls` / `data.image_base64`).

## Requirements

- **Hermes Agent 0.17.0+** (uses the user-plugin loader introduced in
  v0.17 "The Reach Release")
- A **MiniMax Token Plan** API key — get one at
  [`platform.minimax.io/user-center/payment/token-plan`](https://platform.minimax.io/user-center/payment/token-plan).
  The same key works for the `minimax-cn` chat provider too.
- Python 3.10+ (whatever `hermes-agent` itself requires)

## Install (one command)

The fastest way — works on macOS, Linux, WSL, and native Windows:

**macOS / Linux / WSL:**
```bash
curl -fsSL https://raw.githubusercontent.com/Upstream17/hermes-minimax-image-plugin/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Upstream17/hermes-minimax-image-plugin/main/install.ps1 | iex
```

What the scripts do:

1. Detect your OS and the correct plugin directory
   (`%LOCALAPPDATA%\hermes\plugins\image_gen\minimax\` on Windows,
   `~/.hermes/plugins/image_gen/minimax/` on macOS / Linux / WSL — this
   is the path the official `hermes plugins install` command targets
   and the path the plugin loader scans at startup)
2. Copy `__init__.py` and `plugin.yaml` into that directory
3. Run `hermes plugins enable minimax` (the official enable command —
   it registers the plugin in `plugins.enabled` and avoids the
   list-as-string malformation that the older `hermes config set`
   approach hits)
4. Run `hermes config set image_gen.provider minimax` to route
   `image_generate` to this provider
5. **Do not** touch your `MINIMAX_CN_API_KEY` — see the next section
   for the auto-detection rules

### Manual install (no curl pipe — recommended for first-time users)

```bash
# 1. Clone
git clone https://github.com/Upstream17/hermes-minimax-image-plugin.git
cd hermes-minimax-image-plugin
```bash
# 2. Drop the plugin files into the official user-plugin location
#    (this is the path `hermes plugins install` targets and the path the
#    plugin loader scans).
#    macOS / Linux / WSL:
mkdir -p ~/.hermes/plugins/image_gen/minimax
cp plugin/* ~/.hermes/plugins/image_gen/minimax/

#    Windows (PowerShell):
#    New-Item -ItemType Directory -Force -Path "$env:LOCALAPPDATA\hermes\plugins\image_gen\minimax"
#    Copy-Item plugin\* "$env:LOCALAPPDATA\hermes\plugins\image_gen\minimax\"

# 3. Enable the plugin (official command — registers it in plugins.enabled).
hermes plugins enable minimax

# 4. Switch image_generate to the minimax backend.
hermes config set image_gen.provider minimax
```

The `image_gen.model` setting is optional — the plugin defaults to
`image-01` and falls back to it if unset. To use `image-01-live`
instead:

```bash
hermes config set image_gen.model image-01-live
```

## API key — auto-detection

**You usually don't need to do anything.** The plugin checks four sources
in order and uses the first one that resolves to a non-empty key:

1. `MINIMAX_CN_API_KEY` env var
2. `MINIMAX_API_KEY` env var (fallback for users with only the global key)
3. `providers.minimax-cn.api_key` in `config.yaml` — the same key the
   `minimax-cn` chat provider uses. **If you already configured chat
   on Token Plan, the image backend is already keyed. Nothing to do.**
4. `$HERMES_HOME/.env` (`MINIMAX_CN_API_KEY=...` line)

If none of the four is set, the `image_generate` tool returns a clear
`auth_required` error pointing at the env var. To set it manually:

```bash
# macOS / Linux / WSL
echo 'MINIMAX_CN_API_KEY=eyJhbGc...' >> ~/.hermes/.env

# Windows (PowerShell)
Add-Content "$env:LOCALAPPDATA\hermes\.env" 'MINIMAX_CN_API_KEY=eyJhbGc...'
```

> Token Plan note: image and text share one quota. Heavy image use
> reduces your chat budget for the rest of the month.

## Verify it works

```bash
# 1. Plugin loader should report it
HERMES_PLUGINS_DEBUG=1 hermes chat -q "ping" --yolo -Q 2>&1 | grep minimax
# Expected:
# [plugins] INFO Plugin 'minimax' registered image_gen provider: minimax

# 2. Real image generation
hermes chat -q "Generate an image: a small red apple on a white background" --yolo -Q
# Expected: a https://hailuo-image-algeng-data.oss-cn-wulanchabu.aliyuncs.com/.../aigc.jpeg URL
```

## Switching back to a different provider

```bash
hermes config set image_gen.provider fal    # or xai / openai / krea / openai-codex / openrouter
hermes config set image_gen.model fal-ai/flux-2/klein/9b
```

The plugin stays installed but inactive. To fully remove:

```bash
# Easiest:
hermes plugins uninstall minimax

# Or manually:
rm -rf ~/.hermes/plugins/image_gen/minimax       # macOS / Linux / WSL
Remove-Item -Recurse "$env:LOCALAPPDATA\hermes\plugins\image_gen\minimax"  # Windows
```

And remove `- minimax` from `plugins.enabled` in `config.yaml` (or run
`hermes plugins disable minimax`).

## Models

| Model id          | Style                          | T2I | I2I |
|-------------------|--------------------------------|-----|-----|
| `image-01`        | General-purpose, high detail   | ✅  | ✅  |
| `image-01-live`   | Hand-drawn / cartoon emphasis  | ✅  | ❌  |

`image-01` is the default. Switch with
`hermes config set image_gen.model image-01-live`.

## Files in this repo

```
.
├── README.md              # this file (English, for international users)
├── README.zh-CN.md        # Chinese (default for China-region users)
├── LICENSE                # MIT
├── CHANGELOG.md           # version history
├── install.sh             # macOS / Linux / WSL one-liner installer
├── install.ps1            # Windows one-liner installer
├── fix-config-list.py     # belt-and-suspenders fix for old Hermes <0.18 (not needed if you use the installer)
└── plugin/
    ├── __init__.py        # the actual provider code
    └── plugin.yaml        # manifest (name, kind, requires_env)
```

The `plugin/` directory is the installable artifact. The `__init__.py` and
`plugin.yaml` get copied verbatim into your Hermes plugins directory.

## How it works

`agent/image_gen_provider.py` defines an `ImageGenProvider` ABC. Every image
generation backend (FAL, xAI, OpenAI, etc.) implements that interface. This
plugin adds a new implementation that hits the MiniMax `/v1/image_generation`
endpoint with a Bearer token. The endpoint URL is selected at call time
(China by default, global if `MINIMAX_IMAGE_API_URL` is set).

The plugin registers itself at Hermes boot via the standard `register(ctx)`
entry point. The dispatcher in `agent/image_gen_registry.py` selects it when
`image_gen.provider` is set to `minimax`.

See the
[Hermes docs](https://hermes-agent.nousresearch.com/docs/developer-guide/image-gen-provider-plugin)
for the full reference.

## Notes

- **Returned image URLs are signed Aliyun OSS URLs**, valid for ~24h
  (controlled by the `Expires` query param). Save the bytes locally if you
  need durable storage.
- **Token Plan = shared quota.** Image and text share one bucket. Heavy
  image use reduces chat budget for the rest of the month.
- **Real API response shape is `data.image_urls`, not top-level
  `image_urls`.** The official MiniMax docs are wrong about this; the
  parser in this plugin handles the real shape (verified on the China
  endpoint; the global endpoint response shape is assumed to match).
- **Global endpoint is untested by the author.** See the Endpoints
  section above.

## Troubleshooting

**`Plugin 'minimax' registered image_gen provider: minimax` does not appear**
in the verify step. Check:

1. `hermes --version` ≥ 0.17
2. The files are at `~/.hermes/plugins/image_gen/minimax/` — this is
   the path the loader scans (key prefix is `image_gen/`, the final
   directory is the plugin name).
3. `plugins.enabled` in `config.yaml` includes `minimax`:
   ```yaml
   plugins:
     enabled:
       - minimax
   ```
   If the line is malformed (e.g. `enabled: '["minimax"]'` quoted as a
   string), run `python fix-config-list.py` from this repo — it's an
   idempotent YAML fixer for the known `hermes config set` bug in
   Hermes <0.18.

**`MiniMax API key not found`** — none of the four auto-detection sources
matched. Set `MINIMAX_CN_API_KEY` in your environment, or configure the
`minimax-cn` chat provider with `hermes model`.

**`MiniMax returned error: ...` with HTTP 401/403** — your key is set but
the wrong endpoint domain. The China endpoint (`api.minimaxi.com`) takes
China-region keys; the global endpoint (`api.minimax.io`) takes
non-China / pay-as-you-go keys. To switch, set or clear
`MINIMAX_IMAGE_API_URL` (see the Endpoints section).

## Contributing

Issues and PRs welcome. The plugin is intentionally a single file so it's
easy to fork and adapt for other MiniMax endpoints or models.

## License

MIT — see [`LICENSE`](LICENSE).
