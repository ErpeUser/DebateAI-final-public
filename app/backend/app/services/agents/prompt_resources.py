"""Single runtime source for user-editable AI prompts.

The writable ``ai`` directory is authoritative. Database values and built-in
constants are migration/default inputs only, so a file edit and the in-app
editor can never select different hidden prompt versions.
"""

import re

from app.services.ai_config import active_prompt, ai_directory, save_prompt

_SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")


def load_prompt_resource(name: str, fallback: str) -> str:
    """Read the active file on every call and seed it once when missing."""
    if not _SAFE_NAME.fullmatch(name):
        raise ValueError(f"invalid prompt resource name: {name!r}")
    path = ai_directory() / f"{name}.txt"
    value = active_prompt(name, "")
    if value:
        return value
    # Seed only a genuinely missing file.  An invalid user file must remain
    # untouched so a safe fallback cannot silently destroy the user's edit.
    if not path.exists() and fallback.strip():
        try:
            save_prompt(name, fallback)
        except OSError:
            return fallback
    return active_prompt(name, fallback)
