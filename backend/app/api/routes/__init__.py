"""All API routes registered here."""
from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.import_ import router as import_router
from app.api.routes.archive import router as archive_router
from app.api.routes.settings import router as settings_router
from app.api.routes.jobs import router as jobs_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
router.include_router(import_router, prefix="/import", tags=["import"])
router.include_router(archive_router, prefix="/archive", tags=["archive"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
