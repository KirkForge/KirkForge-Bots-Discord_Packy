"""
packy_endpoint.py - FastAPI endpoint for Packy V2.0.0

This endpoint provides HTTP access to PackyBrain with mood/snark integration
based on CPU load and system temperature. It serves as the full orchestration
entry point, combining cognition, mood resolution, lore selection, and final
prompt assembly.

Endpoints:
  POST /respond - Process user text through full pipeline (cognition -> lore -> prompt)
  GET /health - Health check with current mood and brain status
  GET /state - Return current PackyState as JSON
  POST /lore - Retrieve n lore entries filtered by category
"""

import sys
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path so imports work when run from project root
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

# Import PackyBrain and mood engine
from src.cognition.packy_brain import PackyBrain, get_packy
from src.cognition.packy_mood_engine import resolve_packy_state
from src.orchestration.alarm_routes import alarm_router, reminder_router, scheduler_router

# License layer (project root is on sys.path from line 16).
# The product refuses to start without a verified license. The gate
# distinguishes LicenseNotFoundError / LicenseSignatureError /
# LicenseProductMismatchError so the operator gets a clear next step.
import license as _license
from license import (
    LicenseError,
    LicenseNotFoundError,
    LicenseSignatureError,
    LicenseFormatError,
    LicenseProductMismatchError,
    LoadedLicense,
    LicenseClaims,
    Customer,
    PRODUCT_ID,
    TIER_COMMUNITY,
    TIER_FEATURES,
    LICENSE_FORMAT_VERSION,
    load as load_license,
)

# Try to import PackyCogEngine
try:
    from src.cognition.packy_cog_engine import PackyCogEngine
except ImportError:
    PackyCogEngine = None

logger = logging.getLogger("packy.endpoint")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ---- Auth Configuration ----
API_SECRET = os.getenv("PACKY_API_SECRET", "")
_bypass_auth = not API_SECRET  # if no secret set, allow all (dev mode)

if not _bypass_auth:
    logger.warning("PACKY_API_SECRET is set — auth is enabled")
else:
    logger.warning("PACKY_API_SECRET not set — auth is DISABLED (dev mode only, do not use in production)")

def _check_auth_header(headers: dict) -> bool:
    """Check bearer token in Authorization header using timing-safe comparison."""
    if _bypass_auth:
        return True
    import hmac
    auth = headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[7:]  # strip "Bearer "
    return hmac.compare_digest(token, API_SECRET)


# ---- LLM Configuration ----
PRIMARY_ADAPTER = os.getenv("PRIMARY_ADAPTER", "claude")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")

# Product version surfaced via /admin/version. Keep in sync with pyproject.toml.
PRODUCT_VERSION = "2.0.0"

# Initialize FastAPI app
app = FastAPI(
    title="Packy Endpoint",
    description="HTTP interface to Packy Brain with adaptive mood/snark and full cognition pipeline",
    version=PRODUCT_VERSION,
)

# ---- Rate Limiting ----
limiter = Limiter(key_func=get_remote_address, default_limits=[])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global FastAPI middleware for auth (skips /health, /docs, /openapi)
# Registered after app creation — runs at module load
@app.middleware("http")
async def auth_middleware(request, call_next):
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)
    if not _check_auth_header(dict(request.headers)):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    return await call_next(request)

# ---- CORS Configuration ----
# Restrict CORS origins in production. Set PACKY_CORS_ORIGINS env var
# to a comma-separated list of allowed origins (e.g. "https://packy.example.com,https://admin.example.com")
# Default: same-origin only (no CORS headers sent to browsers)
import os as _os
_cors_origins = [o.strip() for o in _os.getenv("PACKY_CORS_ORIGINS", "").split(",") if o.strip()]
if _cors_origins:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )
    import logging as _logging
    _logging.getLogger("packy.endpoint").info("CORS enabled for origins: %s", _cors_origins)

# Global PackyBrain instance
_packy_instance: Optional[PackyBrain] = None
_cog_engine: Optional[PackyCogEngine] = None
_brain_loaded: bool = False
_current_state: Dict[str, Any] = {}
_last_init_attempt: float = 0.0

def get_packy_instance() -> Optional[PackyBrain]:
    """Get or create the global Packy instance, retrying with backoff on failure."""
    global _packy_instance, _last_init_attempt
    if _packy_instance is not None:
        return _packy_instance

    # Rate-limit retries: only attempt once every 30 seconds
    now = time.monotonic()
    if now - _last_init_attempt < 30:
        return None

    _last_init_attempt = now
    try:
        _packy_instance = get_packy()
        logger.info("PackyBrain instance initialized successfully")
    except Exception as e:
        logger.exception("Failed to initialize PackyBrain: %s", e)
        _packy_instance = None
    return _packy_instance

def get_cog_engine() -> Optional[PackyCogEngine]:
    """Get or create the global PackyCogEngine instance."""
    global _cog_engine
    if _cog_engine is None and PackyCogEngine:
        try:
            brain = get_packy_instance()
            _cog_engine = PackyCogEngine(brain=brain)
            logger.info("PackyCogEngine initialized successfully")
        except Exception as e:
            logger.exception("Failed to initialize PackyCogEngine: %s", e)
            _cog_engine = None
    return _cog_engine

def build_metadata_header(state_dict: Dict[str, Any], guild_id: str = "") -> str:
    """
    Build metadata header string in format:
    [CPU=X] [TEMP=Y] [MOOD=Z] [SNARK=W] [GUILD=guild_id]
    """
    cpu_pct = state_dict.get("cpu_pct", 0)
    weather = state_dict.get("weather", "UNKNOWN")
    mood = state_dict.get("mood", "UNKNOWN")
    snark_level = state_dict.get("snark_level", "LOW")

    guild_tag = f" [GUILD={guild_id}]" if guild_id else ""

    return f"[CPU={cpu_pct}] [TEMP={weather}] [MOOD={mood}] [SNARK={snark_level}]{guild_tag}"

def read_live_cpu() -> float:
    """Read current CPU utilisation percent via psutil, or 0.0 if unavailable."""
    if _PSUTIL_AVAILABLE:
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            pass
    return 0.0

def map_snark_to_float(snark_level_str: str) -> float:
    """
    Map snark level string to float value.
    LOW=1, MEDIUM=2.5, HIGH=3.5, MAX=5
    """
    snark_map = {
        "LOW": 1.0,
        "MEDIUM": 2.5,
        "HIGH": 3.5,
        "MAX": 5.0
    }
    return snark_map.get(snark_level_str, 1.0)

async def call_llm(system_prompt: str, user_text: str, max_tokens: int = 800) -> str:
    """
    Call Claude or MiniMax API based on PRIMARY_ADAPTER setting.

    Args:
        system_prompt: System prompt for context and behavior
        user_text: User input text
        max_tokens: Maximum tokens in response (default: 800)

    Returns:
        LLM response text, or fallback string on error
    """
    try:
        if PRIMARY_ADAPTER == "claude":
            return await _call_claude(system_prompt, user_text, max_tokens)
        elif PRIMARY_ADAPTER == "minimax":
            return await _call_minimax(system_prompt, user_text, max_tokens)
        else:
            logger.error("Unknown PRIMARY_ADAPTER: %s", PRIMARY_ADAPTER)
            return "My circuits are fried. Try again, meatbag."
    except Exception as e:
        logger.exception("LLM call failed: %s", e)
        return "My circuits are fried. Try again, meatbag."

async def _call_claude(system_prompt: str, user_text: str, max_tokens: int) -> str:
    """
    Call Claude API via Anthropic.

    Args:
        system_prompt: System prompt for context
        user_text: User input text
        max_tokens: Maximum tokens in response

    Returns:
        Claude response text

    Raises:
        Exception: On API errors
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": user_text
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        # Extract text from response
        if result.get("content") and len(result["content"]) > 0:
            return result["content"][0].get("text", "")

        raise ValueError("No content in Claude response")

async def _call_minimax(system_prompt: str, user_text: str, max_tokens: int) -> str:
    """
    Call MiniMax API.

    Args:
        system_prompt: System prompt for context
        user_text: User input text
        max_tokens: Maximum tokens in response

    Returns:
        MiniMax response text

    Raises:
        Exception: On API errors
    """
    if not MINIMAX_API_KEY:
        raise ValueError("MINIMAX_API_KEY not set")

    url = "https://api.minimaxi.chat/v1/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "MiniMax-Text-01",
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_text
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        # Extract text from response
        if result.get("choices") and len(result["choices"]) > 0:
            return result["choices"][0].get("message", {}).get("content", "")

        raise ValueError("No content in MiniMax response")

# ---- Request/Response models ----

class RespondRequest(BaseModel):
    """User request to Packy with system context."""
    user_text: str = Field(..., min_length=1)
    cpu: float = 0.0
    temp: float = 20.0
    guild_id: str = ""
    user_id: str = ""

class RespondResponse(BaseModel):
    """Response from Packy with full pipeline output."""
    result: str
    state: Dict[str, Any]
    mood: str
    snark: float
    cognition: str
    lore_used: bool
    prompt_preview: str

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    brain_loaded: bool
    mood: Optional[str] = None

class PackyStateResponse(BaseModel):
    """Current Packy state."""
    mood: str
    snark_level: str
    snark_float: float
    cpu_pct: int
    weather: str

class LoreRequest(BaseModel):
    """Lore retrieval request."""
    category: str
    n: int = 3

class LoreEntry(BaseModel):
    """A single lore entry."""
    text: str

class LoreResponse(BaseModel):
    """Lore retrieval response."""
    category: str
    count: int
    entries: List[str]

# ---- License gate ----

# ponytail: dev-bypass for clean-clone boot. No license file + PACKY_DEV_LICENSE=1
# loads a community-tier pseudo-license (lowest tier — nothing to forge) with a
# loud warning, skipping signature verification. Production without the env var
# still exits 1 on a missing file. Ceiling: an operator can always set the env
# var to get community tier, which grants only the free features (core character
# + single-server bot), so the trust cost is nil — forging paid tiers still
# needs a signed file. Upgrade path: ship a signed community license generated
# with `python -m tools.keygen` (requires the dev private key, intentionally not
# in-repo) and drop this bypass.
_DEV_LICENSE_ENV = "PACKY_DEV_LICENSE"


def _dev_license_enabled() -> bool:
    return os.getenv(_DEV_LICENSE_ENV, "").strip().lower() in ("1", "true", "yes")


def _dev_community_license() -> LoadedLicense:
    """Build an unsigned community-tier pseudo-license for dev boot only."""
    now = datetime.now(timezone.utc)
    claims = LicenseClaims(
        license_id="dev-community",
        product=PRODUCT_ID,
        product_version="2.0.0",
        format_version=LICENSE_FORMAT_VERSION,
        customer=Customer(name="Dev", email="dev@local"),
        tier=TIER_COMMUNITY,
        issued_at=now,
        support_until=now + timedelta(days=365),
        max_seats=1,
        features=tuple(TIER_FEATURES[TIER_COMMUNITY]),
    )
    return LoadedLicense(claims=claims, source_path=Path("<dev>"))


def boot_license() -> LoadedLicense:
    """Verify the license at process start. Any failure → exit 1.

    Mirrors the boot flow in The_specialist/main.py: search the standard
    paths, verify the Ed25519 signature against the embedded public key,
    confirm the product field matches `gargoyle-packy`, and stash the
    result in `license.current` so any feature gate downstream can query it.

    Dev bypass: PACKY_DEV_LICENSE=1 with no license file boots a community-tier
    pseudo-license (no signature check). See _dev_community_license.
    """
    try:
        loaded = load_license()
    except LicenseNotFoundError as exc:
        if _dev_license_enabled():
            sys.stderr.write(
                "\n" + "=" * 70 + "\n"
                "  Gargoyle Packy — DEV LICENSE (no signature)\n"
                "  PACKY_DEV_LICENSE=1 set and no license file found.\n"
                "  Booting community tier for local dev. NOT FOR PRODUCTION.\n"
                + "=" * 70 + "\n\n"
            )
            loaded = _dev_community_license()
        else:
            sys.stderr.write("\n" + "=" * 70 + "\n")
            sys.stderr.write("  Gargoyle Packy — LICENSE NOT FOUND\n")
            sys.stderr.write("=" * 70 + "\n\n")
            sys.stderr.write(str(exc) + "\n")
            sys.exit(1)
    except (LicenseSignatureError, LicenseFormatError) as exc:
        sys.stderr.write("\n" + "=" * 70 + "\n")
        sys.stderr.write("  Gargoyle Packy — LICENSE INVALID\n")
        sys.stderr.write("=" * 70 + "\n\n")
        sys.stderr.write(f"  {exc}\n\n")
        sys.stderr.write("  Re-download your license from your kirkforge.com account,\n")
        sys.stderr.write("  or contact support@kirkforge.com for a replacement.\n\n")
        sys.exit(1)
    except LicenseProductMismatchError as exc:
        sys.stderr.write("\n" + "=" * 70 + "\n")
        sys.stderr.write("  Gargoyle Packy — LICENSE WRONG PRODUCT\n")
        sys.stderr.write("=" * 70 + "\n\n")
        sys.stderr.write(f"  {exc}\n\n")
        sys.exit(1)
    except LicenseError as exc:
        sys.stderr.write(f"\nFATAL: license error: {exc}\n")
        sys.exit(1)

    _license.current = loaded
    summary = loaded.summary()
    if not summary["support_active"]:
        sys.stderr.write(
            f"\nWARNING: support contract expired on {summary['support_until']}. "
            f"The product will run, but priority support and update channels "
            f"are unavailable. Renew at https://kirkforge.com/packy/renew.\n\n"
        )
    logger.info(
        "license OK: id=%s tier=%s customer=%s support_until=%s",
        summary["license_id"], summary["tier"],
        summary["customer"], summary["support_until"],
    )
    return loaded


# ---- Startup event ----

@app.on_event("startup")
async def startup_event():
    """Verify license first, then load PackyBrain singleton."""
    boot_license()
    global _brain_loaded
    try:
        brain = get_packy_instance()
        if brain:
            _brain_loaded = True
            logger.info("Packy Brain loaded successfully on startup")
        else:
            _brain_loaded = False
            logger.warning("Packy Brain loaded in degraded mode (functions may be limited)")
    except Exception as e:
        _brain_loaded = False
        logger.exception("Startup warning: Packy Brain initialization incomplete: %s", e)

# ---- Include alarm/reminder/scheduler routers ----
app.include_router(alarm_router, prefix="/alarms")
app.include_router(reminder_router, prefix="/reminders")
app.include_router(scheduler_router, prefix="/scheduler")

# ---- Endpoints ----

@app.post("/respond", response_model=RespondResponse)
@limiter.limit("10/minute")
async def respond(request: RespondRequest, req: Request) -> RespondResponse:
    """
    Process user text through the Packy response pipeline:
    1. Resolve system state (CPU/temp -> mood/snark)
    2. Use PackyCogEngine.think() for stochastic style composition (not LLM reasoning)
    3. Select relevant lore based on text, snark level, and mood
    4. Build metadata header and final prompt
    5. Return assembled prompt and state info

    Args:
        user_text: User message to Packy
        cpu: CPU usage percent (0-100)
        temp: System temperature in Celsius
        guild_id: Optional Discord guild ID
        user_id: Optional Discord user ID

    Returns:
        RespondResponse with result prompt, state, mood, snark, cognition, lore_used, prompt_preview
    """
    try:
        # Step 1: Resolve mood and snark based on system state
        # If caller didn't provide cpu (default 0.0), read from the local machine.
        cpu = request.cpu if request.cpu > 0.0 else read_live_cpu()
        state_dict = resolve_packy_state(
            cpu_pct=int(cpu),
            temp_c=float(request.temp)
        )

        # Update global state cache for /state endpoint
        _current_state.update(state_dict)
        _current_state["cpu_pct"] = int(cpu)

        snark_level_str = state_dict.get("snark_level", "LOW")
        snark_float = map_snark_to_float(snark_level_str)

        # Step 2: Generate cognition text via PackyCogEngine
        cognition_text = ""
        cog_engine = get_cog_engine()
        if cog_engine:
            try:
                cognition_text = cog_engine.think(request.user_text)
                logger.debug("Cognition engine produced reasoning text")
            except Exception as e:
                logger.warning("PackyCogEngine.think() failed; using empty cognition: %s", e)
                cognition_text = f"(Cognition unavailable: {str(e)})"
        else:
            logger.debug("PackyCogEngine not available; skipping cognition phase")
            cognition_text = "(Cognition engine not loaded)"

        # Step 3: Select lore based on text, snark level, and mood
        lore_used = False
        lore_block = ""
        brain = get_packy_instance()
        if brain:
            try:
                # Get snark lines (lore) with optional category detection
                snark_lines = brain.get_snark_lines(n=1)
                if snark_lines:
                    lore_block = snark_lines[0]
                    lore_used = True
                    logger.debug("Selected lore: %s", lore_block[:50])
            except Exception as e:
                logger.warning("Failed to select lore; continuing without: %s", e)
                lore_block = ""
                lore_used = False
        else:
            logger.warning("PackyBrain not available; skipping lore selection")

        # Step 4: Build metadata header
        header = build_metadata_header(state_dict, guild_id=request.guild_id)

        # Step 5: Assemble final prompt
        # Format: header + cognition_text + lore_block + "\nUser: {user_text}\nPacky:"
        assembled_prompt = f"{header}\n{cognition_text}"
        if lore_block:
            assembled_prompt += f"\n\n{lore_block}"
        assembled_prompt += f"\n\nUser: {request.user_text}\nPacky:"

        # Generate preview (first 200 chars)
        prompt_preview = assembled_prompt[:200]
        if len(assembled_prompt) > 200:
            prompt_preview += "..."

        # Step 6: Determine style_limit based on snark level (used for max_tokens)
        # CLIPPED→150, TERSE→400, SNARKY→600, SHORT→800
        style_limit_map = {
            "LOW": 400,       # TERSE
            "MEDIUM": 600,    # SNARKY
            "HIGH": 600,      # SNARKY
            "MAX": 800        # SHORT
        }
        style_limit = style_limit_map.get(snark_level_str, 800)

        # Step 7: Extract system prompt (everything before "\nUser:") and call LLM
        system_prompt = assembled_prompt.split("\nUser:")[0] if "\nUser:" in assembled_prompt else assembled_prompt
        packy_response = await call_llm(system_prompt, request.user_text, max_tokens=style_limit)

        logger.info(
            "Respond: mood=%s, snark=%s, user_id=%s, guild_id=%s, lore_used=%s",
            state_dict.get("mood", "UNKNOWN"),
            snark_level_str,
            request.user_id,
            request.guild_id,
            lore_used
        )

        return RespondResponse(
            result=packy_response,
            state=state_dict,
            mood=state_dict.get("mood", "UNKNOWN"),
            snark=snark_float,
            cognition=cognition_text,
            lore_used=lore_used,
            prompt_preview=prompt_preview
        )

    except Exception as e:
        logger.exception("respond() failed: %s", e)
        fallback_response = "My circuits are fried. Try again, meatbag."
        return RespondResponse(
            result=fallback_response,
            state={"error": str(e), "cpu_pct": int(request.cpu), "weather": "UNKNOWN"},
            mood="GRUMPY",
            snark=1.0,
            cognition="(Error in cognition)",
            lore_used=False,
            prompt_preview="Error"
        )

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with status, brain_loaded flag, and current mood
    """
    try:
        brain = get_packy_instance()
        mood = None
        if brain:
            mood = getattr(brain, "mood", "unknown")

        logger.debug("Health check: brain_loaded=%s, mood=%s", _brain_loaded, mood)

        return HealthResponse(
            status="ok",
            brain_loaded=_brain_loaded,
            mood=mood
        )

    except Exception as e:
        logger.exception("health() failed: %s", e)
        return HealthResponse(
            status="error",
            brain_loaded=False,
            mood=None
        )

@app.get("/state", response_model=PackyStateResponse)
def get_state() -> PackyStateResponse:
    """
    Return current PackyState as JSON.

    Returns:
        PackyStateResponse with mood, snark_level, snark_float, cpu_pct, weather
    """
    try:
        # Use the last resolved state, or return defaults
        mood = _current_state.get("mood", "CALM")
        snark_level = _current_state.get("snark_level", "LOW")
        snark_float = map_snark_to_float(snark_level)
        cpu_pct = _current_state.get("cpu_pct", 0)
        weather = _current_state.get("weather", "NEUTRAL")

        logger.debug("State query: mood=%s, snark=%s", mood, snark_level)

        return PackyStateResponse(
            mood=mood,
            snark_level=snark_level,
            snark_float=snark_float,
            cpu_pct=cpu_pct,
            weather=weather
        )

    except Exception as e:
        logger.exception("get_state() failed: %s", e)
        return PackyStateResponse(
            mood="UNKNOWN",
            snark_level="LOW",
            snark_float=1.0,
            cpu_pct=0,
            weather="UNKNOWN"
        )

@app.post("/lore", response_model=LoreResponse)
def get_lore(request: LoreRequest) -> LoreResponse:
    """
    Retrieve n lore entries filtered by category.

    Args:
        category: Lore category to filter by (or "" for all)
        n: Number of entries to return (default 3)

    Returns:
        LoreResponse with matching entries from the lorebook
    """
    try:
        max(1, min(request.n, 100))

        brain = get_packy_instance()
        if not brain:
            raise HTTPException(status_code=503, detail="PackyBrain not available")

        # Get lore entries
        entries = []
        if request.category:
            # Filter by specific category
            try:
                category_entries = brain._get_lines_for_category(request.category)
                if category_entries:
                    # Random sample up to n
                    import random
                    entries = list(random.sample(
                        category_entries,
                        min(len(category_entries), request.n)
                    ))
                    logger.info("Retrieved %d lore entries from category '%s'", len(entries), request.category)
                else:
                    logger.warning("No entries found for category '%s'", request.category)
                    entries = []
            except Exception as e:
                logger.warning("Failed to retrieve category '%s': %s", request.category, e)
                entries = []
        else:
            # Get general snark lines (mixed categories)
            entries = brain.get_snark_lines(n=request.n)
            logger.info("Retrieved %d general lore entries", len(entries))

        return LoreResponse(
            category=request.category or "general",
            count=len(entries),
            entries=entries
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_lore() failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Lore retrieval failed: {str(e)}")

# ---- Admin endpoints (Conductor-style) -----------------------------------
# These mirror the shape of The_specialist's Conductor /api/* routes. They
# are gated by the same PACKY_API_SECRET auth middleware that protects the
# other endpoints — the loopback-bind default is enforced in __main__.

class AdminLicenseResponse(BaseModel):
    license_id: str
    tier: str
    customer_name: str
    customer_email: str
    max_seats: int
    issued_at: str
    support_until: str
    support_active: bool
    source_path: str


class AdminVersionResponse(BaseModel):
    product: str
    version: str
    manifest_url: str | None = None


@app.get("/admin/license", response_model=AdminLicenseResponse)
def admin_license() -> AdminLicenseResponse:
    """Return the verified license summary, or 503 if the product has no
    license loaded (refuse to start is enforced at boot, so a missing
    license here means the startup event was bypassed — which we want
    to surface, not paper over)."""
    import license as _lic
    if _lic.current is None:
        raise HTTPException(
            status_code=503,
            detail="no license loaded (boot_license() did not run?)",
        )
    s = _lic.current.summary()
    return AdminLicenseResponse(
        license_id=str(s["license_id"]),
        tier=str(s["tier"]),
        customer_name=str(s["customer"]),
        customer_email=str(s["email"]),
        max_seats=int(s["max_seats"]),
        issued_at=str(s["issued_at"]),
        support_until=str(s["support_until"]),
        support_active=bool(s["support_active"]),
        source_path=str(s["source_path"]),
    )


@app.get("/admin/version", response_model=AdminVersionResponse)
def admin_version() -> AdminVersionResponse:
    """Return the product + version. The same value the Conductor surfaces
    in its status bar; useful for `curl | jq` health checks."""
    return AdminVersionResponse(
        product="gargoyle-packy",
        version=PRODUCT_VERSION,
    )


@app.get("/admin/update")
def admin_update() -> dict:
    """Check the signed update channel. Never raises — returns the same
    UpdateCheck dict the standalone `python -m update` CLI prints.

    Honors the PACKY_MANIFEST_URL env var (useful for testing) and
    falls back to the default URL in update/manifest.py.
    """
    from update.checker import check_for_update
    manifest_url = os.environ.get("PACKY_MANIFEST_URL", "").strip() or None
    if manifest_url:
        info = check_for_update(PRODUCT_VERSION, manifest_url=manifest_url)
    else:
        info = check_for_update(PRODUCT_VERSION)
    return info.to_dict()


# ---- Main entry point ----

if __name__ == "__main__":
    port = int(os.getenv("COGNITION_PORT", 8765))
    bind_host = os.getenv("COGNITION_BIND_HOST", "127.0.0.1")
    logger.info(f"Starting Packy Endpoint v2.0.0 on {bind_host}:{port}")
    uvicorn.run(
        app,
        host=bind_host,
        port=port,
        log_level="info"
    )
