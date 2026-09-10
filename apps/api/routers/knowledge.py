import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.database import get_db, AsyncSessionLocal
from apps.api.core.dependencies import get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.workspace import WorkspaceRole
from packages.common.models.knowledge import BusinessProfile, WebsiteScan, KnowledgeChunk, KnowledgeDocument, ScanStatus
from packages.common.schemas.knowledge import (
    WebsiteScanCreateRequest,
    WebsiteScanResponse,
    BusinessProfileResponse,
    BusinessProfileUpdateRequest,
    KnowledgeSearchRequest,
    ChunkSearchResult
)
from packages.ai.embeddings import EmbeddingGenerator
from packages.website_intelligence.crawler_service import WebsiteCrawlerService
from apps.worker.tasks.crawler_tasks import run_website_scan_task

logger = logging.getLogger("codenter.knowledge")

router = APIRouter(tags=["Website Intelligence & Knowledge"])

async def _background_website_scan(workspace_id: str, scan_id: str, base_url: str):
    """Fallback local asynchronous execution of the Website Intelligence crawl pipeline."""
    try:
        async with AsyncSessionLocal() as session:
            await WebsiteCrawlerService.run_scan(
                workspace_id=workspace_id,
                scan_id=scan_id,
                base_url=base_url,
                db=session
            )
            logger.info(f"Local crawl completed successfully for {base_url}")
    except Exception as e:
        logger.error(f"Local crawl failed for {base_url}: {e}")

@router.post("/website-scans", response_model=WebsiteScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_website_scan(
    payload: WebsiteScanCreateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    scan = WebsiteScan(
        workspace_id=ctx.workspace_id,
        url=payload.url,
        status=ScanStatus.PENDING
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Dispatch Celery background worker task, or fallback to asyncio background task
    try:
        run_website_scan_task.delay(
            workspace_id=ctx.workspace_id,
            scan_id=scan.id,
            base_url=payload.url
        )
    except Exception as err:
        logger.warning(f"Celery dispatch failed ({err}). Spawning local asyncio crawl task...")
        asyncio.create_task(_background_website_scan(ctx.workspace_id, scan.id, payload.url))

    return scan

@router.get("/website-scans/latest", response_model=WebsiteScanResponse | None)
async def get_latest_website_scan(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(WebsiteScan)
        .where(WebsiteScan.workspace_id == ctx.workspace_id)
        .order_by(WebsiteScan.created_at.desc())
    )
    return res.scalars().first()

@router.get("/website-scans/{scan_id}", response_model=WebsiteScanResponse)
async def get_website_scan_status(
    scan_id: str,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    # CRITICAL: Always enforce workspace_id == ctx.workspace_id
    res = await db.execute(
        select(WebsiteScan).where(
            WebsiteScan.id == scan_id,
            WebsiteScan.workspace_id == ctx.workspace_id
        )
    )
    scan = res.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Website scan not found")
    return scan

@router.get("/business-profile", response_model=BusinessProfileResponse)
async def get_active_business_profile(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    # CRITICAL: Always enforce workspace_id == ctx.workspace_id
    res = await db.execute(
        select(BusinessProfile).where(
            BusinessProfile.workspace_id == ctx.workspace_id,
            BusinessProfile.is_active == True
        )
    )
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="No active Business Profile found. Initiate a website scan first."
        )
    return profile

@router.put("/business-profile", response_model=BusinessProfileResponse)
async def update_business_profile(
    payload: BusinessProfileUpdateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(BusinessProfile).where(
            BusinessProfile.workspace_id == ctx.workspace_id,
            BusinessProfile.is_active == True
        )
    )
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="No active Business Profile to update")

    # Update provided fields
    update_dict = payload.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(profile, field, value)

    profile.version += 1
    await db.commit()
    await db.refresh(profile)
    return profile

@router.post("/knowledge/search", response_model=list[ChunkSearchResult])
async def search_knowledge_chunks(
    payload: KnowledgeSearchRequest,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    RAG Vector similarity search over workspace knowledge chunks with source citations.
    """
    query_emb = await EmbeddingGenerator.get_embedding(payload.query)

    # Query all chunks belonging to the current workspace
    res = await db.execute(
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeChunk.workspace_id == ctx.workspace_id)
    )
    rows = res.all()

    scored = []
    for chunk, doc in rows:
        sim = 0.0
        if chunk.embedding:
            sim = EmbeddingGenerator.cosine_similarity(query_emb, chunk.embedding)
        scored.append((chunk, doc, sim))

    # Sort descending by similarity
    scored.sort(key=lambda x: x[2], reverse=True)

    results = []
    for chunk, doc, sim in scored[:payload.top_k]:
        results.append(ChunkSearchResult(
            chunk_id=chunk.id,
            document_id=doc.id,
            content=chunk.content,
            source_url=chunk.metadata_json.get("source_url", doc.url),
            title=doc.title,
            score=round(float(sim), 4)
        ))

    return results
