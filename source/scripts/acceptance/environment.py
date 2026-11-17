"""Minimal inherited environment; all mutable profile paths are synthetic."""
import os
from pathlib import Path


def isolated_environment(source: Path, output: Path) -> dict:
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'LANG', 'LC_ALL', 'VIRTUAL_ENV'}
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    paths = {'HOME': 'home', 'USERPROFILE': 'home', 'APPDATA': 'roaming',
             'LOCALAPPDATA': 'local', 'TEMP': 'tmp', 'TMP': 'tmp', 'TMPDIR': 'tmp',
             'HF_HOME': 'huggingface', 'XDG_CONFIG_HOME': 'config', 'XDG_CACHE_HOME': 'cache'}
    for key, name in paths.items():
        target = output / 'synthetic-profile' / name
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        environment[key] = str(target)
    environment.update(PYTHONUTF8='1', PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', GOOGLE_GENAI_USE_VERTEXAI='false',
        GEMINI_API_KEY='', GOOGLE_API_KEY='', OPENAI_API_KEY='', OPENAI_COMPATIBLE_API_KEY='',
        ANTHROPIC_API_KEY='', GOOGLE_APPLICATION_CREDENTIALS='', GIT_TERMINAL_PROMPT='0',
        DEBATEAI_DESKTOP='0', DEBATEAI_INSTANCE_TOKEN='', SUBSCRIPTION_BRIDGE_BUDGET_FALLBACK='false',
        DEBATEAI_SUBSCRIPTION_BRIDGE_KEY='', DEBATEAI_SUBSCRIPTION_BRIDGE_URL='',
        DATABASE_URL='postgresql+asyncpg://synthetic:synthetic@127.0.0.1:1/synthetic',
        DEBATEAI_DATA_DIR=str(output / 'synthetic-data'), DATA_DIR=str(output / 'synthetic-data' / 'data'),
        PYTHONPATH=os.pathsep.join(str(source / part) for part in ('', 'backend', 'desktop')))
    return environment


def has_user_dotenv(cwd: Path, environment: dict) -> bool:
    """Check dotenv discovery roots and ancestors without reading their contents.

    The adapter invokes reviewed project commands, not arbitrary untrusted code.
    Explicit secret-file reads elsewhere are not contained by an environment map.
    """
    roots = {cwd.absolute()}
    for raw in environment.get('PYTHONPATH', '').split(os.pathsep):
        if raw:
            path = Path(raw)
            roots.add(path.absolute() if path.is_absolute() else (cwd / path).absolute())
    candidates = set()
    for root in roots:
        candidates.update((root, *root.parents))
    return any(os.path.lexists(str(parent / '.env')) for parent in candidates)
