import logging
import httpx
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

class WebsiteCrawlerService:
    MAX_PAGES_TO_CRAWL = 10

    @classmethod
    async def run_scan(
        cls,
        workspace_id: str,
        scan_id: str,
        base_url: str,
        db: AsyncSession,
        mock_client: httpx.AsyncClient | None = None
    ) -> WebsiteScan:
        # Load scan record
        scan_res = await db.execute(select(WebsiteScan).where(WebsiteScan.id == scan_id))
        scan = scan_res.scalar_one()

        scan.status = ScanStatus.IN_PROGRESS
        await db.commit()

        normalized_base = URLNormalizer.normalize(base_url)
        crawled_pages: list[FetchedPage] = []
        failed_count = 0

        owns_client = False
        client = mock_client
        if client is None:
            client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
            owns_client = True

        try:
            # 1. Robots check
            robots = RobotsParser()
            await robots.fetch_and_parse(normalized_base, client=client)

            # 2. Discover URLs via Sitemap + prioritize
            discovered = await SitemapCrawler.discover_urls(normalized_base, client=client)
            scan.pages_discovered = len(discovered)
            await db.commit()

            # 3. Filter URLs permitted by robots and limit to top N
            target_urls = [
                u for u, prio in discovered if robots.can_fetch(u)
            ][:cls.MAX_PAGES_TO_CRAWL]

            # Guarantee that base_url is always included in target URLs
            if not target_urls or normalized_base not in target_urls:
                target_urls.insert(0, normalized_base)
            target_urls = target_urls[:cls.MAX_PAGES_TO_CRAWL]

            # 4. Crawl prioritized pages with dynamic internal link discovery
            scan.status = ScanStatus.CRAWLING
            await db.commit()

            visited: set[str] = set()
            idx = 0
            while idx < len(target_urls) and len(crawled_pages) < cls.MAX_PAGES_TO_CRAWL:
                url = target_urls[idx]
                idx += 1
                if url in visited:
                    continue
                visited.add(url)

                try:
                    page = await HybridPageFetcher.fetch(url, client=client)
                    crawled_pages.append(page)

                    # Persist KnowledgeDocument
                    doc = KnowledgeDocument(
                        workspace_id=workspace_id,
                        url=page.url,
                        title=page.cleaned.title or "Web Page",
                        content_hash=page.cleaned.content_hash,
                        source_type="WEBSITE",
                        raw_text=page.cleaned.text,
                        screenshot_url=page.screenshot_url
                    )
                    db.add(doc)
                    await db.flush()

                    # Chunk and Embed
                    chunks = SemanticChunker.chunk_text(page.cleaned.text, source_url=page.url, title=page.cleaned.title)
                    for c in chunks:
                        emb = await EmbeddingGenerator.get_embedding(c.content)
                        k_chunk = KnowledgeChunk(
                            workspace_id=workspace_id,
                            document_id=doc.id,
                            chunk_index=c.chunk_index,
                            content=c.content,
                            token_count=c.token_count,
                            embedding=emb,
                            metadata_json=c.metadata
                        )
                        db.add(k_chunk)

                    # Dynamic internal link discovery from page content
                    if len(target_urls) < cls.MAX_PAGES_TO_CRAWL:
                        for in_link in page.cleaned.internal_links:
                            norm_in = URLNormalizer.normalize(in_link)
                            if (
                                URLNormalizer.is_same_domain(normalized_base, norm_in)
                                and norm_in not in visited
                                and norm_in not in target_urls
                            ):
                                if robots.can_fetch(norm_in):
                                    target_urls.append(norm_in)
                                    if len(target_urls) >= cls.MAX_PAGES_TO_CRAWL:
                                        break

                except Exception as e:
                    logger.warning(f"Failed crawling page {url}: {e}")
                    failed_count += 1

            scan.pages_discovered = max(scan.pages_discovered, len(target_urls), len(visited))
            scan.pages_crawled = len(crawled_pages)
            scan.pages_failed = failed_count

            if not crawled_pages:
                scan.status = ScanStatus.FAILED
                scan.error_message = "No pages could be crawled from the target URL"
                await db.commit()
                return scan

            # 5. Extract structured BusinessProfile
            scan.status = ScanStatus.EXTRACTING
            await db.commit()

            extracted_data = BusinessExtractor.extract_from_pages(crawled_pages)

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
                    scan_obj.error_message = str(e)[:500]
                    await db.commit()
                    return scan_obj
            except Exception as commit_err:
                logger.error(f"Failed to record failure status for scan {scan_id}: {commit_err}")
            return scan
        finally:
            if owns_client:
                await client.aclose()
