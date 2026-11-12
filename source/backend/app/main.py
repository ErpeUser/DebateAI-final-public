import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.models import Base
from app.release_notes import APP_VERSION
from app.routers import agents, ai_config, analyze, artifacts, ask, chat, chatgpt_web, credentials, debate_review, debate_settings, dossiers, retranscribe, diagnostics, directives, documents, endpoints, gemini_web, groups, imports, knowledge, meta, model_downloads, models, native_audio, offerings, pii_shield, privacy, questions, sessions, speakers, subscription_accounts, synthesis, transcripts, updates
from app.services.pii.egress import PiiEgressBlocked
from app.services.pii.reveal_middleware import PiiRevealMiddleware
from app.services.privacy import LocalOnlyModeError
from app.services.llm import LLMModelNotSelected
from app.services.audio_store import (
    audio_file_path,
    cleanup_orphan_track_audio,
    repair_wav_file,
)
from app.routers import calibration
from app.services.diagnostic_upload_limit import DiagnosticUploadLimitMiddleware
from app.services import redaction, request_guard, runtime_activity
from app.ws import audio_handler

logging.basicConfig(level=logging.INFO)
# Every log record in the process scrubs provider keys before any handler
# formats it (root stream, the desktop file log, uvicorn's own loggers).
redaction.install_log_redaction()
# httpx logs every request URL at INFO and websockets echoes handshake
# headers (including Authorization) at DEBUG; neither may drop below INFO
# even if the root level is lowered for debugging.
for _name in ("httpx", "httpcore", "websockets", "websockets.client"):
    logging.getLogger(_name).setLevel(logging.INFO)


def _add_revalidation_model_columns(connection, inspector, tables):
    if "speaker_revalidation_batches" not in tables:
        return
    columns = {
        c["name"] for c in inspector.get_columns("speaker_revalidation_batches")
    }
    for column in ("requested_model_id", "model_id"):
        if column not in columns:
            connection.execute(
                text(
                    f"ALTER TABLE speaker_revalidation_batches "
                    f"ADD COLUMN {column} VARCHAR(160)"
                )
            )


def _add_thinking_token_column(connection, inspector, tables):
    """Backfill token_usage columns added after the table shipped.

    thinking_tokens predates ALP-284; audio_seconds predates ALP-300, which
    gave duration-billed models (OpenAI Realtime transcription) somewhere to
    land instead of being discarded. The cached and audio token slices let
    the cost estimate price those tokens at their own published rates instead
    of the text rate.

    Extracted rather than inlined with its siblings: _check_and_add is a long
    chain of table/column guards already sitting at the structural complexity
    ceiling, and two more branches pushed it over.
    """
    if "token_usage" not in tables:
        return
    columns = {c["name"] for c in inspector.get_columns("token_usage")}
    if "thinking_tokens" not in columns:
        connection.execute(
            text("ALTER TABLE token_usage ADD COLUMN thinking_tokens INTEGER NOT NULL DEFAULT 0")
        )
    if "audio_seconds" not in columns:
        connection.execute(
            text("ALTER TABLE token_usage ADD COLUMN audio_seconds DOUBLE PRECISION NOT NULL DEFAULT 0")
        )
    for column in ("cached_input_tokens", "audio_input_tokens", "audio_output_tokens"):
        if column not in columns:
            connection.execute(
                text(f"ALTER TABLE token_usage ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0")
            )


def _add_transcript_refinement_columns(connection, inspector, tables) -> None:
    """raw_text and refined_at on transcript_entries (transcript refiner, v0.6.0)."""
    if "transcript_entries" not in tables:
        return
    columns = {c["name"] for c in inspector.get_columns("transcript_entries")}
    if "raw_text" not in columns:
        connection.execute(text("ALTER TABLE transcript_entries ADD COLUMN raw_text TEXT"))
    if "refined_at" not in columns:
        connection.execute(text("ALTER TABLE transcript_entries ADD COLUMN refined_at TIMESTAMP WITH TIME ZONE"))


async def _add_missing_columns(conn):
    """Add columns that create_all won't add to existing tables."""
    from sqlalchemy import inspect

    def _check_and_add(connection):
        inspector = inspect(connection)
        tables = inspector.get_table_names()

        if "questions" in tables:
            columns = {c["name"] for c in inspector.get_columns("questions")}
            if "agent_source" not in columns:
                connection.execute(
                    text("ALTER TABLE questions ADD COLUMN agent_source VARCHAR(30) NOT NULL DEFAULT 'general'")
                )
            if "offering_match" not in columns:
                connection.execute(
                    text("ALTER TABLE questions ADD COLUMN offering_match TEXT NOT NULL DEFAULT ''")
                )
            if "vote" not in columns:
                connection.execute(
                    text("ALTER TABLE questions ADD COLUMN vote INTEGER NOT NULL DEFAULT 0")
                )
            if "speaker_id" not in columns:
                connection.execute(
                    text("ALTER TABLE questions ADD COLUMN speaker_id UUID REFERENCES speakers(id)")
                )
            if "enhanced" not in columns:
                connection.execute(
                    text("ALTER TABLE questions ADD COLUMN enhanced BOOLEAN NOT NULL DEFAULT false")
                )
            if "lens_label" not in columns:
                connection.execute(
                    text("ALTER TABLE questions ADD COLUMN lens_label VARCHAR(120) NOT NULL DEFAULT ''")
                )
                # Custom lens types need more room than the original enum-ish column
                connection.execute(
                    text("ALTER TABLE questions ALTER COLUMN item_type TYPE VARCHAR(50)")
                )

        _add_transcript_refinement_columns(connection, inspector, tables)

        if "speakers" in tables:
            columns = {c["name"] for c in inspector.get_columns("speakers")}
            if "display_name" not in columns:
                connection.execute(
                    text("ALTER TABLE speakers ADD COLUMN display_name VARCHAR(255) NOT NULL DEFAULT ''")
                )
            if "display_name_enabled" not in columns:
                connection.execute(
                    text("ALTER TABLE speakers ADD COLUMN display_name_enabled BOOLEAN NOT NULL DEFAULT false")
                )
            if "speaker_type" not in columns:
                connection.execute(
                    text("ALTER TABLE speakers ADD COLUMN speaker_type VARCHAR(20) NOT NULL DEFAULT 'external'")
                )
                connection.execute(
                    text("UPDATE speakers SET speaker_type = 'team' WHERE is_user = true")
                )

        if "offerings" in tables:
            columns = {c["name"] for c in inspector.get_columns("offerings")}
            if "tags" not in columns:
                if "practice" in columns:
                    connection.execute(
                        text("ALTER TABLE offerings RENAME COLUMN practice TO tags")
                    )
                else:
                    connection.execute(
                        text("ALTER TABLE offerings ADD COLUMN tags VARCHAR(255) NOT NULL DEFAULT ''")
                    )
            if "note" not in columns:
                if "delivery_model" in columns:
                    connection.execute(
                        text("ALTER TABLE offerings RENAME COLUMN delivery_model TO note")
                    )
                    connection.execute(
                        text("ALTER TABLE offerings ALTER COLUMN note TYPE VARCHAR(255)")
                    )
                else:
                    connection.execute(
                        text("ALTER TABLE offerings ADD COLUMN note VARCHAR(255) NOT NULL DEFAULT ''")
                    )
            if "discipline" in columns:
                # Merge the legacy discipline column into subcategory, then drop it.
                connection.execute(
                    text("ALTER TABLE offerings ALTER COLUMN subcategory TYPE VARCHAR(255)")
                )
                connection.execute(
                    text(
                        "UPDATE offerings SET subcategory = discipline "
                        "WHERE subcategory = '' AND discipline <> ''"
                    )
                )
                connection.execute(text("ALTER TABLE offerings DROP COLUMN discipline"))

        if "agent_configs" in tables:
            columns = {c["name"] for c in inspector.get_columns("agent_configs")}
            if "interval_seconds" not in columns:
                connection.execute(
                    text("ALTER TABLE agent_configs ADD COLUMN interval_seconds INTEGER")
                )
            if "knowledge_source_ids" not in columns:
                connection.execute(
                    text("ALTER TABLE agent_configs ADD COLUMN knowledge_source_ids TEXT NOT NULL DEFAULT ''")
                )
            if "lenses" not in columns:
                connection.execute(
                    text("ALTER TABLE agent_configs ADD COLUMN lenses TEXT NOT NULL DEFAULT ''")
                )
            if "model_intervals" not in columns:
                connection.execute(
                    text("ALTER TABLE agent_configs ADD COLUMN model_intervals TEXT NOT NULL DEFAULT ''")
                )
            if "knowledge_source_id" in columns:
                # Migrate and drop the legacy single-source column (its FK would
                # otherwise block deleting knowledge sources).
                connection.execute(
                    text(
                        "UPDATE agent_configs SET knowledge_source_ids = knowledge_source_id::text "
                        "WHERE knowledge_source_id IS NOT NULL AND knowledge_source_ids = ''"
                    )
                )
                connection.execute(
                    text("ALTER TABLE agent_configs DROP COLUMN knowledge_source_id")
                )

        if "sessions" in tables:
            columns = {c["name"] for c in inspector.get_columns("sessions")}
            if "meeting_type" not in columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN meeting_type VARCHAR(50) NOT NULL DEFAULT 'general'")
                )
            if "meeting_context" not in columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN meeting_context TEXT NOT NULL DEFAULT ''")
                )
            if "group_id" not in columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN group_id UUID REFERENCES session_groups(id)")
                )
            if "speaker_context_dirty" not in columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN speaker_context_dirty BOOLEAN NOT NULL DEFAULT false")
                )
            if "drain_summary" not in columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN drain_summary TEXT NOT NULL DEFAULT ''")
                )
            if "speaker_context_enhanced_at" not in columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN speaker_context_enhanced_at TIMESTAMP WITH TIME ZONE")
                )
            if "speaker_context_version" not in columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN speaker_context_version INTEGER NOT NULL DEFAULT 0")
                )

        if "questions" in tables:
            columns = {c["name"] for c in inspector.get_columns("questions")}
            if "speaker_mapping_revision_id" not in columns:
                connection.execute(
                    text("ALTER TABLE questions ADD COLUMN speaker_mapping_revision_id UUID")
                )

        if "session_syntheses" in tables:
            columns = {c["name"] for c in inspector.get_columns("session_syntheses")}
            if "speaker_mapping_revision_id" not in columns:
                connection.execute(
                    text("ALTER TABLE session_syntheses ADD COLUMN speaker_mapping_revision_id UUID")
                )
            if "signal_history" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE session_syntheses "
                        "ADD COLUMN signal_history JSON NOT NULL DEFAULT '[]'"
                    )
                )

        if "custom_endpoints" in tables:
            columns = {c["name"] for c in inspector.get_columns("custom_endpoints")}
            if "deleted_at" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE custom_endpoints "
                        "ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE"
                    )
                )

        if "documents" in tables:
            columns = {c["name"] for c in inspector.get_columns("documents")}
            if "summary" not in columns:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN summary TEXT NOT NULL DEFAULT ''")
                )
            if "summary_source" not in columns:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN summary_source VARCHAR(20) NOT NULL DEFAULT ''")
                )

        _add_revalidation_model_columns(connection, inspector, tables)
        _add_thinking_token_column(connection, inspector, tables)

        # Model ids for self-hosted endpoints ("endpoint:<slug>:<model name>")
        # are longer than the registry ids these columns were sized for.
        for table in ("agent_configs", "token_usage"):
            if table in tables:
                width = next(
                    (c for c in inspector.get_columns(table) if c["name"] == "model_id"), {}
                ).get("type")
                if getattr(width, "length", 0) and width.length < 160:
                    connection.execute(
                        text(f"ALTER TABLE {table} ALTER COLUMN model_id TYPE VARCHAR(160)")
                    )

        if "call_segments" in tables:
            columns = {c["name"] for c in inspector.get_columns("call_segments")}
            if "audio_path" not in columns:
                connection.execute(
                    text("ALTER TABLE call_segments ADD COLUMN audio_path VARCHAR(500)")
                )
            if "mic_audio_path" not in columns:
                connection.execute(
                    text("ALTER TABLE call_segments ADD COLUMN mic_audio_path VARCHAR(500)")
                )
            if "system_audio_path" not in columns:
                connection.execute(
                    text("ALTER TABLE call_segments ADD COLUMN system_audio_path VARCHAR(500)")
                )

    await conn.run_sync(_check_and_add)


async def _cleanup_orphan_audio(conn):
    from sqlalchemy import text

    result = await conn.execute(
        text(
            "SELECT mic_audio_path, system_audio_path FROM call_segments "
            "WHERE mic_audio_path IS NOT NULL OR system_audio_path IS NOT NULL"
        )
    )
    referenced = {path for row in result for path in row if path}
    removed = cleanup_orphan_track_audio(referenced)
    if removed:
        logging.info("Removed %s orphan auxiliary audio files", removed)


async def _recover_interrupted_audio(conn):
    """Relink and repair archive files left by a process crash.

    A segment row is created before capture starts, while its audio paths are
    indexed only when normal finalization runs. On startup, open rows therefore
    provide the stable session/segment identity needed to recover files that
    were already fsynced. Invalid files are left untouched and logged rather
    than being presented as complete audio.
    """
    result = await conn.execute(
        text(
            "SELECT id, session_id, segment_number, audio_path, "
            "mic_audio_path, system_audio_path FROM call_segments "
            "WHERE ended_at IS NULL"
        )
    )
    for row in result:
        fields = {
            "audio_path": row.audio_path,
            "mic_audio_path": row.mic_audio_path,
            "system_audio_path": row.system_audio_path,
        }
        tracks = (("audio_path", "mixed"), ("mic_audio_path", "mic"), ("system_audio_path", "sys"))
        recovered = False
        for field, track in tracks:
            if fields[field]:
                continue
            path = audio_file_path(row.session_id, row.segment_number, track)
            if not path.exists():
                continue
            if not repair_wav_file(path):
                logging.error("Could not validate interrupted audio archive %s", path)
                continue
            fields[field] = str(path.relative_to(path.parents[2])).replace("\\", "/")
            recovered = True
        if not recovered:
            continue
        await conn.execute(
            text(
                "UPDATE call_segments SET audio_path=:audio_path, "
                "mic_audio_path=:mic_audio_path, system_audio_path=:system_audio_path, "
                "ended_at=CURRENT_TIMESTAMP WHERE id=:id"
            ),
            {"id": row.id, **fields},
        )
        logging.warning(
            "Recovered interrupted audio segment %s from durable archive files",
            row.id,
        )


def _backend_root(module_path: str | Path = __file__) -> Path:
    return Path(module_path).resolve().parents[1]


def _schema_startup_action(
    tables: set[str],
) -> Literal["bootstrap", "upgrade", "adopt"]:
    """Bootstrap empty DBs, migrate versioned DBs, and adopt legacy schemas."""
    if not tables:
        return "bootstrap"
    return "upgrade" if "alembic_version" in tables else "adopt"


async def _run_schema_migrations() -> None:
    """Use Alembic normally; adopt old create_all databases once."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync: set(inspect(sync).get_table_names()))
    startup_action = _schema_startup_action(tables)
    if startup_action in {"bootstrap", "adopt"}:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if startup_action == "adopt":
                await _add_missing_columns(conn)

    backend_root = _backend_root()
    config = Config(str(backend_root / "alembic.ini"))
    # Embedded migrations share the launcher's process. Alembic's default
    # fileConfig call would otherwise close the desktop FileHandler, making a
    # healthy startup look frozen and hiding all later diagnostics.
    config.attributes["configure_logger"] = False
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    if startup_action == "upgrade":
        await asyncio.to_thread(command.upgrade, config, "head")
    elif startup_action == "adopt":
        # create_all/_add_missing_columns establish the current legacy shape,
        # but create_all cannot add constraints to existing tables. Adopt at
        # the revision immediately before the constraint migration so 029 is
        # executed instead of incorrectly stamping the database past it.
        await asyncio.to_thread(command.stamp, config, "028_debate_claim_records")
        await asyncio.to_thread(command.upgrade, config, "head")
    else:
        # A fresh create_all database includes every model constraint.
        await asyncio.to_thread(command.stamp, config, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    with runtime_activity.track("startup schema"):
        await _run_schema_migrations()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _recover_interrupted_audio(conn)
            await _cleanup_orphan_audio(conn)

    # Seed agent configs and knowledge sources
    from app.database import async_session
    from app.services.llm_endpoint import migrate_legacy_endpoint
    from app.services.pii.vault import migrate_legacy_entries
    from app.services.seed_agents import (
        configure_desktop_debate_runtime,
        seed_agent_configs,
    )
    from app.services.seed_knowledge import seed_knowledge_sources
    from app.services.subscription_bridge import sync_subscription_bridge
    async with async_session() as db:
        await seed_agent_configs(db)
        await configure_desktop_debate_runtime(db)
        await seed_knowledge_sources(db)
        # One-time: promote a pre-existing single OpenAI-compatible endpoint
        # into a named endpoint so its model shows up in the model pickers.
        await migrate_legacy_endpoint(db)
        migrated_pii_rows = await migrate_legacy_entries(db)
        if migrated_pii_rows:
            logging.getLogger(__name__).info("Migrated %s legacy PII vault rows", migrated_pii_rows)
        await sync_subscription_bridge(db)
        await db.commit()
    ai_config._ensure_static_prompts()

    # Verify untested provider API keys in the background so model
    # availability reflects real connection status, not just key presence.
    import asyncio

    from app.services.provider_health import verify_untested_provider_keys
    verify_task = asyncio.create_task(verify_untested_provider_keys())
    update_task = updates.start_background_check()
    # With the PII Shield on, have the on-device NER model ready before the
    # first transcript segment rather than downloading it mid-call.
    from app.services.pii.shield import warm_up_ner

    async def _warm_up_ner():
        async with async_session() as db:
            await warm_up_ner(db)

    ner_task = asyncio.create_task(_warm_up_ner())

    yield
    from app.services.windows_audio_capture import native_windows_audio
    await native_windows_audio.stop()
    from app.services.subscription_bridge import cleanup_gemini_web_cookie
    cleanup_gemini_web_cookie()
    from app.services.debate_research import close_research_client
    await close_research_client()
    verify_task.cancel()
    ner_task.cancel()
    updates.stop_background_check(update_task)
    await engine.dispose()


app = FastAPI(title="DebateAI", version=APP_VERSION, lifespan=lifespan)

# The API has no login, so the browser's same-origin policy is the only thing
# between a hostile web page and the user's transcripts and provider budget.
# CORS therefore admits local origins only (plus DEBATEAI_ALLOWED_ORIGINS);
# the frontend is always served same-origin (nginx proxy, Vite proxy, or the
# backend itself on desktop), so nothing legitimate needs a wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=request_guard.cors_allowed_origins(),
    allow_origin_regex=request_guard.CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
updates.configure_app(app)
# Session-scoped JSON responses get their protected values substituted back
# for the person at this machine; every reveal is audited.
app.add_middleware(PiiRevealMiddleware)
app.add_middleware(DiagnosticUploadLimitMiddleware)
# Outermost: a request with a foreign Host (DNS rebinding) or a foreign
# Origin on a state-changing method never reaches a router.
app.add_middleware(request_guard.RequestGuardMiddleware)

app.include_router(sessions.router)
app.include_router(agents.router)
app.include_router(ai_config.router)
app.include_router(groups.router)
app.include_router(directives.router)
app.include_router(documents.router)
app.include_router(questions.router)
app.include_router(transcripts.router)
app.include_router(speakers.router)
app.include_router(
    synthesis.router,
    dependencies=[Depends(runtime_activity.request_tracker("briefing synthesis"))],
)
app.include_router(offerings.router)
app.include_router(knowledge.router)
app.include_router(
    artifacts.router,
    dependencies=[Depends(runtime_activity.request_tracker("artifact export"))],
)
app.include_router(
    imports.router,
    dependencies=[Depends(runtime_activity.request_tracker("import"))],
)
app.include_router(
    analyze.router,
    dependencies=[Depends(runtime_activity.request_tracker("analysis"))],
)
app.include_router(models.router)
app.include_router(meta.router)
app.include_router(credentials.router)
app.include_router(endpoints.router)
app.include_router(gemini_web.router)
app.include_router(chatgpt_web.router)
app.include_router(subscription_accounts.router)
app.include_router(
    retranscribe.router,
    dependencies=[Depends(runtime_activity.request_tracker("retranscription"))],
)
app.include_router(chat.router)
app.include_router(ask.router)
app.include_router(diagnostics.router)
app.include_router(calibration.router)
app.include_router(privacy.router)
app.include_router(debate_settings.router)
app.include_router(dossiers.router)
app.include_router(debate_review.router)
app.include_router(native_audio.router)
app.include_router(pii_shield.router)
app.include_router(pii_shield.session_router)
app.include_router(model_downloads.router)
app.include_router(updates.router)
app.include_router(audio_handler.router)


@app.exception_handler(LocalOnlyModeError)
async def local_only_mode_handler(request: Request, exc: LocalOnlyModeError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(LLMModelNotSelected)
async def model_not_selected_handler(request: Request, exc: LLMModelNotSelected):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(PiiEgressBlocked)
async def pii_egress_blocked_handler(request: Request, exc: PiiEgressBlocked):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/api/health")
async def health():
    return {"status": "ok"}


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@app.get("/api/ready")
async def readiness():
    if await _database_ready():
        return {"status": "ok"}
    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "database": "unavailable"},
    )


def mount_frontend(application: FastAPI, dist_dir: str) -> None:
    """Serve the built frontend from the backend (native desktop mode)."""
    if not dist_dir:
        return
    from fastapi.staticfiles import StaticFiles

    application.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")


mount_frontend(app, settings.FRONTEND_DIST)
