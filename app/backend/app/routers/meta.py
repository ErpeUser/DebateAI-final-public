from app.release_notes import APP_VERSION, RELEASE_NOTES
from fastapi import APIRouter

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("")
def get_meta():
    return {"version": APP_VERSION}


@router.get("/release-notes")
def list_release_notes():
    return RELEASE_NOTES
