# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-06-30

### Fixed
- **Install path.** The official `hermes plugins` CLI and the plugin
  loader both target `~/.hermes/plugins/image_gen/<name>/`. Earlier
  scripts targeted the bare `plugins/<name>/` path, which is silently
  ignored by the loader. Installers and README now point at the
  correct path. End-to-end verified via `hermes plugins uninstall`
  → reinstall via `install.ps1` → successful image generation
  through MiniMax image-01.

### Changed
- **Version reset to 0.1.1.** The plugin works end-to-end but is a
  vibe-coded single-file drop-in, not a stable release — 0.1.x
  reflects that.
- **Bilingual READMEs.** `README.md` (English, primary) points to
  `README.zh.md` (Chinese, vibe-toned, Hermes × MiniMax collab
  framing) at the top.
- **README copy.** English version is the primary landing page;
  Chinese version is a casual / 协作者 voice instead of a spec doc.
  All technical info preserved in both.

## [0.1.0] - 2026-06-20

### Added
- Initial release.
- MiniMax (China region) image generation provider (`minimax` name).
- Models: `image-01` (T2I + I2I) and `image-01-live` (T2I only).
- Aspect ratios: `landscape` (16:9), `square` (1:1), `portrait` (9:16).
- Bearer-token authentication via `MINIMAX_CN_API_KEY` env var.
- I2I support for `image-01` (single source image — base64, HTTPS
  URL, or local path).
- API key auto-detection across 4 sources: env var
  (`MINIMAX_CN_API_KEY` / fallback `MINIMAX_API_KEY`) →
  `providers.minimax-cn.api_key` in `config.yaml` → `$HERMES_HOME/.env`.
  If the `minimax-cn` chat provider is already configured on Token
  Plan, the image backend is keyed automatically.
- One-line installers: `install.sh` (macOS / Linux / WSL) and
  `install.ps1` (Windows).
- Manual-install instructions and verification recipes in
  `README.md`.
- `fix-config-list.py` belt-and-suspenders helper for the
  `hermes config set` list-as-string bug on Hermes <0.18.
- MIT license.
