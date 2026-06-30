"""MiniMax image generation backend.

Exposes MiniMax's ``image-01`` and ``image-01-live`` models as an
:class:`ImageGenProvider` implementation.

Endpoints
---------
The plugin defaults to the China-region endpoint
(``https://api.minimaxi.com/v1/image_generation``). To use the global
endpoint (``https://api.minimax.io/v1/image_generation``) instead —
for users on a non-China Token Plan or pay-as-you-go key — set:

    export MINIMAX_IMAGE_API_URL=https://api.minimax.io/v1/image_generation

(or add it to ``$HERMES_HOME/.env``).

> **Untested note.** Only the China endpoint has been verified
> end-to-end by the author. The global endpoint is supported per
> MiniMax's published docs
> (https://platform.minimax.io/docs/guides/image-generation), but the
> model catalog, response shape, and key types may differ slightly.
> If a global-endpoint user hits an issue, check the docs first —
> the plugin's parser is written against the China response shape.

Features:
- Text-to-image generation (T2I)
- Image-to-image / image editing (I2I) — same endpoint, pass ``image_url``
- Two models:
    image-01         general-purpose, supports both T2I and I2I
    image-01-live    hand-drawn / cartoon style emphasis, T2I only

API key auto-detection (first hit wins):
1. ``MINIMAX_CN_API_KEY`` env var
2. ``MINIMAX_API_KEY`` env var (fallback for users with only the global key)
3. ``providers.minimax-cn.api_key`` in ``config.yaml`` (the same key the
   ``minimax-cn`` chat provider uses; Token Plan covers both text and image)
4. ``~/.hermes/.env`` (``MINIMAX_CN_API_KEY=...`` line)

If none of the above is set, the provider reports ``auth_required`` and
the image_generate tool tells the user to set the env var (or run
``hermes model`` to configure the ``minimax-cn`` chat provider, which will
also satisfy this plugin's key requirement — Token Plan shares one quota
across text and image).

Aspect-ratio mapping (Hermes standard → MiniMax API):
    landscape → 16:9
    square    → 1:1
    portrait  → 9:16
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    normalize_reference_images,
    resolve_aspect_ratio,
    save_b64_image,
    success_response,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default endpoint: China region. Override with the env var
# ``MINIMAX_IMAGE_API_URL`` to use the global endpoint
# (``https://api.minimax.io/v1/image_generation``) for non-China users.
# See the module docstring — the global endpoint is documented by
# MiniMax but not tested end-to-end by the author.
DEFAULT_API_URL = "https://api.minimaxi.com/v1/image_generation"
DEFAULT_TIMEOUT = 120  # seconds

# Environment variable that overrides the default endpoint. Set it to
# ``https://api.minimax.io/v1/image_generation`` to route through the
# MiniMax global endpoint instead of the China endpoint.
API_URL_ENV_VAR = "MINIMAX_IMAGE_API_URL"

# ---------------------------------------------------------------------------
# Model catalog
# ---------------------------------------------------------------------------

_MODELS: Dict[str, Dict[str, Any]] = {
    "image-01": {
        "display": "MiniMax image-01",
        "speed": "~10-20s",
        "strengths": "General-purpose T2I + I2I, fine detail rendering",
        "supports_edit": True,
    },
    "image-01-live": {
        "display": "MiniMax image-01-live",
        "speed": "~10-20s",
        "strengths": "Hand-drawn / cartoon style enhancement, T2I only",
        "supports_edit": False,
    },
}

DEFAULT_MODEL = "image-01"

# Map Hermes's three standard aspect ratios to MiniMax API strings.
_MINIMAX_ASPECT_RATIOS = {
    "landscape": "16:9",
    "square": "1:1",
    "portrait": "9:16",
}


# ---------------------------------------------------------------------------
# Config / model resolution
# ---------------------------------------------------------------------------


def _load_minimax_config() -> Dict[str, Any]:
    """Read ``image_gen.minimax`` from config.yaml."""
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
        section = cfg.get("image_gen") if isinstance(cfg, dict) else None
        mm_section = section.get("minimax") if isinstance(section, dict) else None
        return mm_section if isinstance(mm_section, dict) else {}
    except Exception as exc:
        logger.debug("Could not load image_gen.minimax config: %s", exc)
        return {}


def _resolve_model() -> Tuple[str, Dict[str, Any]]:
    """Decide which model to use and return ``(model_id, meta)``.

    Precedence: env var → image_gen.minimax.model config → default.
    """
    env_override = os.environ.get("MINIMAX_IMAGE_MODEL")
    if env_override and env_override in _MODELS:
        return env_override, _MODELS[env_override]

    cfg = _load_minimax_config()
    candidate = cfg.get("model") if isinstance(cfg.get("model"), str) else None
    if candidate and candidate in _MODELS:
        return candidate, _MODELS[candidate]

    return DEFAULT_MODEL, _MODELS[DEFAULT_MODEL]


# ---------------------------------------------------------------------------
# API-key auto-detection
# ---------------------------------------------------------------------------


def _read_env_file(env_path: Path) -> Dict[str, str]:
    """Parse a ``KEY=value`` env file into a dict. Comments (``#``) and blank
    lines are ignored. Values are stripped; surrounding quotes removed.

    This is intentionally tiny — we only need a handful of keys, and pulling
    in ``dotenv`` would be over-engineering for a single file the user
    controls.
    """
    out: Dict[str, str] = {}
    if not env_path.is_file():
        return out
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.debug("Could not read %s: %s", env_path, exc)
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip a single layer of matching surrounding quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def _hermes_home() -> Path:
    """Resolve ``$HERMES_HOME`` with sensible fallbacks for each platform."""
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home)
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "hermes"
    return Path.home() / ".hermes"


def _key_from_config_yaml() -> Optional[str]:
    """Read ``providers.minimax-cn.api_key`` from config.yaml.

    The ``minimax-cn`` chat provider stores its API key there. Token Plan
    keys are shared between text and image, so a key already configured for
    chat satisfies this plugin automatically — no separate setup needed.
    """
    try:
        from hermes_cli.config import load_config
    except Exception as exc:
        logger.debug("hermes_cli.config not importable: %s", exc)
        return None
    try:
        cfg = load_config()
    except Exception as exc:
        logger.debug("load_config() failed: %s", exc)
        return None
    if not isinstance(cfg, dict):
        return None
    providers = cfg.get("providers")
    if not isinstance(providers, dict):
        return None
    mm_cn = providers.get("minimax-cn")
    if not isinstance(mm_cn, dict):
        return None
    key = mm_cn.get("api_key")
    if isinstance(key, str) and key.strip():
        return key.strip()
    return None


def _key_from_env_file() -> Optional[str]:
    """Read ``MINIMAX_CN_API_KEY`` from ``$HERMES_HOME/.env``."""
    env_vars = _read_env_file(_hermes_home() / ".env")
    for candidate in ("MINIMAX_CN_API_KEY", "MINIMAX_API_KEY"):
        val = env_vars.get(candidate)
        if val and val.strip():
            return val.strip()
    return None


def _resolve_api_url() -> str:
    """Pick the endpoint URL: ``MINIMAX_IMAGE_API_URL`` env var, falling
    back to :data:`DEFAULT_API_URL` (China region).

    Users on a non-China Token Plan or pay-as-you-go key should set
    ``MINIMAX_IMAGE_API_URL=https://api.minimax.io/v1/image_generation``
    to route through the global endpoint.
    """
    env_override = os.environ.get(API_URL_ENV_VAR)
    if isinstance(env_override, str) and env_override.strip():
        return env_override.strip()
    return DEFAULT_API_URL


def _get_api_key() -> str:
    """Resolve the MiniMax China API key from the first available source.

    Precedence (first non-empty wins):
    1. ``MINIMAX_CN_API_KEY`` env var
    2. ``MINIMAX_API_KEY`` env var (fallback for the global key, which works
       against ``api.minimaxi.com`` too)
    3. ``providers.minimax-cn.api_key`` in ``config.yaml`` (Token Plan
       chat provider key — covers image under the same quota)
    4. ``$HERMES_HOME/.env`` ``MINIMAX_CN_API_KEY`` / ``MINIMAX_API_KEY``
    """
    for source in (
        os.environ.get("MINIMAX_CN_API_KEY"),
        os.environ.get("MINIMAX_API_KEY"),
        _key_from_config_yaml(),
        _key_from_env_file(),
    ):
        if isinstance(source, str) and source.strip():
            return source.strip()
    return ""


# ---------------------------------------------------------------------------
# Source-image loading (for I2I)
# ---------------------------------------------------------------------------


def _minimax_image_field(source: str) -> Dict[str, str]:
    """Build the MiniMax ``image`` field for an I2I request.

    MiniMax's I2I endpoint accepts ``{"image": "<base64-or-url>"}``. Public
    URLs pass through; local file paths are read and base64-encoded.
    """
    source = source.strip()
    lower = source.lower()
    if lower.startswith(("http://", "https://")):
        return {"image": source}
    if lower.startswith("data:"):
        # Already a data URI — strip the prefix and pass raw b64.
        _, _, b64 = source.partition(",")
        return {"image": b64}
    # Local file path → base64.
    import base64

    with open(source, "rb") as fh:
        raw = fh.read()
    return {"image": base64.b64encode(raw).decode("utf-8")}


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class MinimaxImageGenProvider(ImageGenProvider):
    """MiniMax (China region) image generation backend — image-01 / image-01-live."""

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def display_name(self) -> str:
        return "MiniMax (China)"

    def is_available(self) -> bool:
        return bool(_get_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": model_id,
                "display": meta["display"],
                "speed": meta["speed"],
                "strengths": meta["strengths"],
            }
            for model_id, meta in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "MiniMax (China + Global)",
            "badge": "paid",
            "tag": (
                "image-01 / image-01-live. Defaults to China endpoint "
                "(api.minimaxi.com); set MINIMAX_IMAGE_API_URL to use the "
                "global endpoint (api.minimax.io) for non-China keys. "
                "China endpoint tested by author; global endpoint is "
                "documented but unverified — see README."
            ),
            "env_vars": [
                {
                    "key": "MINIMAX_CN_API_KEY",
                    "prompt": (
                        "MiniMax API key — leave blank if your "
                        "minimax-cn chat provider is already configured"
                    ),
                    "url": "https://platform.minimax.io/user-center/payment/token-plan",
                },
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        # image-01 supports I2I (single source image per docs).
        # image-01-live is T2I only; we surface the conservative max.
        return {"modalities": ["text", "image"], "max_reference_images": 1}

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate an image (T2I) or edit a source image (I2I)."""
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)

        if not prompt:
            return error_response(
                error="Prompt is required and must be a non-empty string",
                error_type="invalid_argument",
                provider=self.name,
                aspect_ratio=aspect,
            )

        api_key = _get_api_key()
        if not api_key:
            return error_response(
                error=(
                    "MiniMax API key not found. Set MINIMAX_CN_API_KEY in your "
                    "environment, configure the minimax-cn chat provider "
                    "(`hermes model`), or add it to $HERMES_HOME/.env."
                ),
                error_type="auth_required",
                provider=self.name,
                aspect_ratio=aspect,
            )

        model_id, meta = _resolve_model()
        mm_ar = _MINIMAX_ASPECT_RATIOS.get(aspect, "1:1")

        # Pick the primary source image: explicit image_url wins, else the
        # first reference image.
        source_image = None
        if isinstance(image_url, str) and image_url.strip():
            source_image = image_url.strip()
        else:
            refs = normalize_reference_images(reference_image_urls)
            if refs:
                source_image = refs[0]
        is_edit = bool(source_image)
        modality = "image" if is_edit else "text"

        # image-01-live doesn't support I2I per official model description.
        if is_edit and not meta.get("supports_edit", True):
            return error_response(
                error=(
                    f"Model '{model_id}' does not support image-to-image / editing. "
                    "Use 'image-01' for I2I, or call without a source image for T2I."
                ),
                error_type="unsupported_modality",
                provider=self.name,
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        payload: Dict[str, Any] = {
            "model": model_id,
            "prompt": prompt,
            "aspect_ratio": mm_ar,
            "response_format": "url",  # prefer URL; fall back to b64 if absent
        }
        if is_edit:
            try:
                img_field = _minimax_image_field(source_image)
            except Exception as exc:
                return error_response(
                    error=f"Could not load source image for editing: {exc}",
                    error_type="io_error",
                    provider=self.name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )
            payload.update(img_field)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        api_url = _resolve_api_url()

        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            resp = exc.response
            status = resp.status_code if resp is not None else 0
            try:
                # MiniMax returns {"base_resp": {"status_code": ..., "status_msg": "..."}, ...}
                err_body = resp.json() if resp is not None else {}
                base = err_body.get("base_resp") or {}
                err_msg = (
                    base.get("status_msg")
                    or err_body.get("error", {}).get("message")
                    or (resp.text[:300] if resp is not None else str(exc))
                )
            except Exception:
                err_msg = resp.text[:300] if resp is not None else str(exc)
            logger.error("MiniMax image gen failed (%d): %s", status, err_msg)
            return error_response(
                error=f"MiniMax image generation failed ({status}): {err_msg}",
                error_type="api_error",
                provider=self.name,
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )
        except requests.Timeout:
            return error_response(
                error=f"MiniMax image generation timed out ({DEFAULT_TIMEOUT}s)",
                error_type="timeout",
                provider=self.name,
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )
        except requests.ConnectionError as exc:
            return error_response(
                error=f"MiniMax connection error: {exc}",
                error_type="connection_error",
                provider=self.name,
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        try:
            result = response.json()
        except Exception as exc:
            return error_response(
                error=f"MiniMax returned invalid JSON: {exc}",
                error_type="invalid_response",
                provider=self.name,
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        # Parse response. Per MiniMax real API shape (verified 2026-06-20):
        #   {
        #     "id": "...",
        #     "data": {"image_urls": ["https://..."],   "image_base64": [...]},
        #     "metadata": {"success_count": "1", "failed_count": "0"},
        #     "base_resp": {"status_code": 0, "status_msg": "success"}
        #   }
        # We prefer URL (lighter); fall back to b64 if URL is empty.
        data_section = result.get("data") or {}
        urls = data_section.get("image_urls") or []
        b64s = data_section.get("image_base64") or []
        # base_resp may report per-image status
        base = result.get("base_resp") or {}
        if base.get("status_code") not in (None, 0, 1000) and not urls and not b64s:
            return error_response(
                error=f"MiniMax returned error: {base.get('status_msg', 'unknown')}",
                error_type="api_error",
                provider=self.name,
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        if urls:
            image_ref = urls[0]
        elif b64s:
            try:
                saved_path = save_b64_image(b64s[0], prefix=f"minimax_{model_id}")
            except Exception as exc:
                return error_response(
                    error=f"Could not save image to cache: {exc}",
                    error_type="io_error",
                    provider=self.name,
                    model=model_id,
                    prompt=prompt,
                    aspect_ratio=aspect,
                )
            image_ref = str(saved_path)
        else:
            return error_response(
                error="MiniMax response contained neither image_urls nor image_base64",
                error_type="empty_response",
                provider=self.name,
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        return success_response(
            image=image_ref,
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
            provider=self.name,
            modality=modality,
        )


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


def register(ctx) -> None:
    """Plugin entry point — wire ``MinimaxImageGenProvider`` into the registry."""
    ctx.register_image_gen_provider(MinimaxImageGenProvider())
