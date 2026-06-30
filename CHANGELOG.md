# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-06-30

### Fixed
- **Install path.** The official `hermes plugins` CLI and the plugin
  loader both target `~/.hermes/plugins/image_gen/<name>/`. v1.1.0
  scripts targeted the bare `plugins/<name>/` path, which is
  silently ignored by the loader. Installers and README now point
  at the correct path. End-to-end verified via
  `hermes plugins uninstall` → reinstall via `install.ps1` →
  successful image generation through MiniMax image-01.

## [1.1.0] - 2026-06-30

### Changed
- Plugin now installs to the official user-plugin path
  `~/.hermes/plugins/image_gen/minimax/` (was
  `~/.hermes/plugins/minimax/`, which is a legacy path no longer
  recognized by Hermes 0.17+).
- Installers use the official `hermes plugins enable` command instead
  of manually editing `plugins.enabled` (avoids the known
  list-as-string malformation in Hermes <0.18).
- README rewritten to match the official image-gen-provider-plugin
  documentation; `YOUR_USERNAME` placeholders replaced with the repo owner's GH handle and verified URL
  `Upstream17` and verified GitHub repo URL.

### Added
- **API key auto-detection.** The provider now resolves the key from
  four sources in order: `MINIMAX_CN_API_KEY` env, `MINIMAX_API_KEY`
  env, `providers.minimax-cn.api_key` in `config.yaml`, and
  `$HERMES_HOME/.env`. If the `minimax-cn` chat provider is already
  configured on Token Plan, the image backend is keyed automatically
  with no extra setup.
- `get_setup_schema` now reflects the auto-detection behavior in the
  picker tag (no separate key needed when chat is configured).
- New `Troubleshooting` section in README.

## [1.0.0] - 2026-06-20

### Added
- Initial release
- MiniMax China region image generation provider (`minimax` name)
- Models: `image-01` (T2I + I2I) and `image-01-live` (T2I only)
- Aspect ratios: `landscape` (16:9), `square` (1:1), `portrait` (9:16)
- Bearer-token authentication via `MINIMAX_CN_API_KEY` env var
- I2I support for `image-01` (single source image, base64 or HTTPS URL or local path)
- One-line installer for macOS / Linux / WSL (`install.sh`)
- One-line installer for Windows native (`install.ps1`)
- Manual-install instructions in `README.md`
- Verification recipes in `README.md`
- `fix-config-list.py` belt-and-suspenders helper for the
  `hermes config set` list bug on Hermes <0.18
- MIT license
