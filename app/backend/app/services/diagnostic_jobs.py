"""Shared single-flight diagnostic admission, using existing runtime tracking."""
from fastapi import HTTPException

from app.services import runtime_activity
from app.services.calibration_runner import SingleFlight, CalibrationBusy

lane = SingleFlight()


async def run_diagnostic(work, *, timeout=180):
    async def owned(stop):
        with runtime_activity.exclusive('calibration / diagnostic benchmark'):
            return await work(stop)
    try:
        return await lane.run(owned, timeout=timeout)
    except (CalibrationBusy, runtime_activity.ShutdownReserved) as exc:
        raise HTTPException(409, str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(504, 'Diagnostic timed out; native work may still be draining. Check status before retrying.') from exc
