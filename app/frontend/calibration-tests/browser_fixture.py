from pathlib import Path


PUBLIC = Path(__file__).resolve().parents[1] / "public"


def load_calibration_modules(page):
    """Execute the lab in the synthetic DOM without a network navigation."""
    scripts = PUBLIC / "calibration"
    core = (scripts / "core.mjs").read_text(encoding="utf-8").replace("export ", "")
    session = (scripts / "session.mjs").read_text(encoding="utf-8").replace("export ", "")
    lab = (scripts / "lab.mjs").read_text(encoding="utf-8").split("\n", 2)[2]
    page.add_script_tag(type="module", content="\n".join((
        core, session, lab, "window.__calibrationModuleLoaded = true;",
    )))
    page.wait_for_function("window.__calibrationModuleLoaded === true")
