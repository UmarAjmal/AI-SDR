import asyncio
import logging
import httpx
from typing import Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.knowledge import BusinessProfile, KnowledgeDocument, KnowledgeChunk, WebsiteScan, ScanStatus
from packages.website_intelligence.normalizer import URLNormalizer
from packages.website_intelligence.robots import RobotsParser
from packages.website_intelligence.sitemap import SitemapCrawler
from packages.website_intelligence.fetcher import HybridPageFetcher, FetchedPage
from packages.ai.chunking import SemanticChunker
from packages.ai.embeddings import EmbeddingGenerator
from packages.ai.extractors.business_extractor import BusinessExtractor

logger = logging.getLogger("codenter.crawler.service")

def _clean_pg_text(val: Any) -> str:
    if val is None:
        return ""
    return str(val).replace("\x00", "").replace("\u0000", "")

def _clean_pg_data(data: Any) -> Any:
    if isinstance(data, str):
        return data.replace("\x00", "").replace("\u0000", "")
    elif isinstance(data, dict):
        return {_clean_pg_text(k): _clean_pg_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_clean_pg_data(item) for item in data]
    return data

class WebsiteCrawlerService:
    # Section 4.1 Crawl Pipeline: Comprehensive crawling up to 50 prioritized pages
    MAX_PAGES_TO_CRAWL = 50
    CONCURRENCY_LIMIT = 5

    @classmethod
    async def run_scan(
        cls,
        workspace_id: str,
        scan_id: str,
        base_url: str,
        db: AsyncSession,
        mock_client: httpx.AsyncClient | None = None,
        max_pages: int | None = None
    ) -> WebsiteScan:
        crawl_limit = max_pages or cls.MAX_PAGES_TO_CRAWL

        # Load scan record
        scan_res = await db.execute(select(WebsiteScan).where(WebsiteScan.id == scan_id))
        scan = scan_res.scalar_one()

        scan.status = ScanStatus.IN_PROGRESS
        await db.commit()

        # Step 17: Validate URL and normalize domain
        normalized_base = URLNormalizer.normalize(base_url)
        crawled_pages: list[FetchedPage] = []
        failed_count = 0

        owns_client = False
        client = mock_client
        if client is None:
            client = httpx.AsyncClient(timeout=20.0, follow_redirects=True)
            owns_client = True

        try:
            # Step 18: Fetch robots.txt and apply crawl policy
            robots = RobotsParser()
            await robots.fetch_and_parse(normalized_base, client=client)

            # Step 19 & 20: Discover sitemap.xml and child sitemaps with prioritization
            discovered = await SitemapCrawler.discover_urls(normalized_base, client=client)
            scan.pages_discovered = len(discovered)
            await db.commit()

            # Target URLs prioritized and filtered by robots
            target_urls: list[str] = [
                u for u, prio in discovered if robots.can_fetch(u)
            ]

            # Guarantee that base_url / homepage is always included first
            if not target_urls or normalized_base not in target_urls:
                target_urls.insert(0, normalized_base)

            scan.status = ScanStatus.CRAWLING
            await db.commit()

            visited: set[str] = set()
            semaphore = asyncio.Semaphore(cls.CONCURRENCY_LIMIT)

            async def fetch_single_page(url_to_crawl: str) -> FetchedPage | None:
                async with semaphore:
                    try:
                        return await HybridPageFetcher.fetch(url_to_crawl, client=client)
                    except Exception as fe:
                        logger.warning(f"Failed crawling page {url_to_crawl}: {fe}")
                        return None

            # Crawl prioritized pages with concurrent batch processing and dynamic internal link discovery
            while target_urls and len(crawled_pages) < crawl_limit:
                # Get next batch of unvisited URLs
                batch = []
                while target_urls and len(batch) < cls.CONCURRENCY_LIMIT and (len(crawled_pages) + len(batch)) < crawl_limit:
                    next_url = target_urls.pop(0)
                    if next_url not in visited:
                        visited.add(next_url)
                        batch.append(next_url)

                if not batch:
                    break

                # Concurrently fetch the batch
                results = await asyncio.gather(*[fetch_single_page(u) for u in batch])

                for page in results:
                    if page is None:
                        failed_count += 1
                        continue

                    crawled_pages.append(page)

                    # Step 22 & 28: Persist KnowledgeDocument
                    doc = KnowledgeDocument(
                        workspace_id=workspace_id,
                        url=_clean_pg_text(page.url),
                        title=_clean_pg_text(page.cleaned.title or "Web Page")[:500],
                        content_hash=page.cleaned.content_hash,
                        source_type="WEBSITE",
                        raw_text=_clean_pg_text(page.cleaned.text),
                        screenshot_url=_clean_pg_text(page.screenshot_url) if page.screenshot_url else None,
                        fetched_at=page.fetched_at
                    )
                    db.add(doc)
                    await db.flush()

                    # Step 27: Semantic Chunking & pgvector Embeddings
                    chunks = SemanticChunker.chunk_text(
                        text=_clean_pg_text(page.cleaned.text),
                        source_url=_clean_pg_text(page.url),
                        title=_clean_pg_text(page.cleaned.title),
                        page_type=page.cleaned.page_type,
                        business_topic=page.cleaned.business_topic,
                        extraction_timestamp=page.fetched_at.isoformat()
                    )

                    for c in chunks:
                        emb = await EmbeddingGenerator.get_embedding(c.content)
                        k_chunk = KnowledgeChunk(
                            workspace_id=workspace_id,
                            document_id=doc.id,
                            chunk_index=c.chunk_index,
                            content=_clean_pg_text(c.content),
                            token_count=c.token_count,
                            embedding=emb,
                            metadata_json=_clean_pg_data(c.metadata)
                        )
                        db.add(k_chunk)

                    # Dynamic internal link discovery from page content (Rule 19)
                    for in_link in page.cleaned.internal_links:
                        norm_in = URLNormalizer.normalize(in_link)
                        if (
                            URLNormalizer.is_same_domain(normalized_base, norm_in)
                            and norm_in not in visited
                            and norm_in not in target_urls
                        ):
                            if robots.can_fetch(norm_in):
                                # Prioritize new link
                                p_score = SitemapCrawler.prioritize_url(norm_in)
                                if p_score >= 50:
                                    target_urls.insert(0, norm_in)
                                else:
                                    target_urls.append(norm_in)

                # Commit batch progress
                scan.pages_discovered = max(scan.pages_discovered, len(visited) + len(target_urls))
                scan.pages_crawled = len(crawled_pages)
                scan.pages_failed = failed_count
                await db.commit()

            if not crawled_pages:
                scan.status = ScanStatus.FAILED
                scan.error_message = "No pages could be crawled from the target URL"
                await db.commit()
                return scan

            # Step 26, 28, 29: Extract structured facts with provenance and confidence gate
            scan.status = ScanStatus.EXTRACTING
            await db.commit()

            extracted_data = BusinessExtractor.extract_from_pages(crawled_pages)
            extracted_data = _clean_pg_data(extracted_data)

            # Check if active profile exists
            existing_prof_res = await db.execute(
                select(BusinessProfile).where(
                    BusinessProfile.workspace_id == workspace_id,
                    BusinessProfile.is_active == True
                )
            )
            existing_prof = existing_prof_res.scalar_one_or_none()

            if existing_prof:
                # Update existing profile
                existing_prof.company_name = extracted_data["company_name"]
                existing_prof.description = extracted_data["description"]
                existing_prof.offerings = extracted_data["offerings"]
                existing_prof.value_propositions = extracted_data["value_propositions"]
                existing_prof.industries = extracted_data["industries"]
                existing_prof.icp_hints = extracted_data["icp_hints"]
                existing_prof.pricing = extracted_data["pricing"]
                existing_prof.features = extracted_data["features"]
                existing_prof.faqs = extracted_data["faqs"]
                existing_prof.proof = extracted_data["proof"]
                existing_prof.brand_voice = extracted_data["brand_voice"]
                existing_prof.claims_policy = extracted_data["claims_policy"]
                existing_prof.ctas = extracted_data["ctas"]
                existing_prof.confidence_score = extracted_data["confidence_score"]
                existing_prof.version += 1
            else:
                # Create new profile
                new_prof = BusinessProfile(
                    workspace_id=workspace_id,
                    company_name=extracted_data["company_name"],
                    description=extracted_data["description"],
                    offerings=extracted_data["offerings"],
                    value_propositions=extracted_data["value_propositions"],
                    industries=extracted_data["industries"],
                    icp_hints=extracted_data["icp_hints"],
                    pricing=extracted_data["pricing"],
                    features=extracted_data["features"],
                    faqs=extracted_data["faqs"],
                    proof=extracted_data["proof"],
                    brand_voice=extracted_data["brand_voice"],
                    claims_policy=extracted_data["claims_policy"],
                    ctas=extracted_data["ctas"],
                    confidence_score=extracted_data["confidence_score"],
                    version=1,
                    is_active=True
                )
                db.add(new_prof)

            scan.status = ScanStatus.PARTIAL_FAILURE if failed_count > 0 else ScanStatus.COMPLETED
            await db.commit()
            await db.refresh(scan)
            return scan

        except Exception as e:
            logger.error(f"Fatal error during website scan {scan_id}: {e}")
            try:
                await db.rollback()
                scan_res = await db.execute(select(WebsiteScan).where(WebsiteScan.id == scan_id))
                scan_obj = scan_res.scalar_one_or_none()
                if scan_obj:
                    scan_obj.status = ScanStatus.FAILED
                    scan_obj.error_message = _clean_pg_text(str(e))[:500]
                    await db.commit()
                    return scan_obj
            except Exception as commit_err:
                logger.error(f"Failed to record failure status for scan {scan_id}: {commit_err}")
            return scan
        finally:
            if owns_client:
                await client.aclose()
