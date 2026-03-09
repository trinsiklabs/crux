#!/usr/bin/env python3
"""crux-ingest: Universal Ingestion Pipeline for knowledge extraction.

PLAN-352: Universal Ingestion Pipeline
any source -> normalized knowledge -> research expansion -> synthesis -> Onelist knowledge graph

Architecture:
1. Input normalization (all inputs to markdown)
2. Content triage (LLM relevance scoring, entity extraction, quality filter)
3. Research expansion (Jina search for context, cross-reference existing entries)
4. Synthesis (standardized report: insights, knowledge, implications, related entries, action items)
5. Knowledge graph integration (entry_type=knowledge, relational links in metadata, bidirectional linking, initiative tags)
6. Ripple updates (detect contradictions, update related entries, flag stale info)
7. Auto-QCP (generate plans from new insights)

Supported sources:
- Web URLs (via Jina Reader)
- X/Twitter threads
- Markdown files
- HTML files
- PDF files
- Google Docs (via export URL)

CLI: crux ingest <url|file>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

USER_ID = "4269c6ad-d52b-4930-b496-f3f1d65e98b2"  # Key's Onelist user
JINA_READER_PREFIX = "https://r.jina.ai/"
DATABASE = "key_onelist"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class IngestSource:
    """Represents an ingestion source."""
    source_type: str  # url, x_thread, markdown, html, pdf, gdoc
    original_input: str
    normalized_url: str | None = None
    file_path: str | None = None


@dataclass
class NormalizedContent:
    """Content normalized to markdown."""
    title: str
    content: str  # Markdown
    source_url: str | None = None
    source_type: str = ""
    raw_metadata: dict = field(default_factory=dict)
    extracted_at: str = ""


@dataclass
class TriagedContent:
    """Content after LLM triage."""
    relevance_score: float  # 0-1
    quality_score: float  # 0-1
    entities: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    key_insights: list[str] = field(default_factory=list)
    should_ingest: bool = True
    rejection_reason: str | None = None


@dataclass
class ExpandedContent:
    """Content after research expansion."""
    related_searches: list[dict] = field(default_factory=list)
    existing_entries: list[dict] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    supporting_evidence: list[dict] = field(default_factory=list)


@dataclass
class SynthesizedReport:
    """Final synthesis report."""
    title: str
    summary: str
    insights: list[str] = field(default_factory=list)
    knowledge_claims: list[str] = field(default_factory=list)
    implications: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    related_entries: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_url: str | None = None
    confidence: float = 0.8


@dataclass
class IngestResult:
    """Result of ingestion pipeline."""
    success: bool
    entry_id: str | None = None
    public_id: str | None = None
    title: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_links: list[str] = field(default_factory=list)
    suggested_plans: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 1: Input Normalization
# ---------------------------------------------------------------------------

def detect_source_type(input_str: str) -> IngestSource:
    """Detect the type of input source."""
    input_str = input_str.strip()

    # Check if it's a file path
    if os.path.exists(input_str):
        path = Path(input_str)
        ext = path.suffix.lower()
        if ext == ".md":
            return IngestSource(source_type="markdown", original_input=input_str, file_path=str(path.absolute()))
        elif ext == ".html":
            return IngestSource(source_type="html", original_input=input_str, file_path=str(path.absolute()))
        elif ext == ".pdf":
            return IngestSource(source_type="pdf", original_input=input_str, file_path=str(path.absolute()))
        else:
            # Treat as text/markdown
            return IngestSource(source_type="markdown", original_input=input_str, file_path=str(path.absolute()))

    # Check if it's a URL
    parsed = urlparse(input_str)
    if parsed.scheme in ("http", "https"):
        # Detect specific URL types
        if "twitter.com" in parsed.netloc or "x.com" in parsed.netloc:
            return IngestSource(source_type="x_thread", original_input=input_str, normalized_url=input_str)
        elif "docs.google.com" in parsed.netloc:
            return IngestSource(source_type="gdoc", original_input=input_str, normalized_url=input_str)
        else:
            return IngestSource(source_type="url", original_input=input_str, normalized_url=input_str)

    # Assume raw markdown text
    return IngestSource(source_type="raw_text", original_input=input_str)


def fetch_url_content(url: str) -> tuple[str, dict]:
    """Fetch URL content using Jina Reader."""
    jina_url = f"{JINA_READER_PREFIX}{url}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(jina_url, headers={
                "Accept": "text/markdown",
            })
            response.raise_for_status()

            content = response.text

            # Parse Jina response format
            metadata = {}
            lines = content.split("\n")
            content_start = 0

            for i, line in enumerate(lines):
                if line.startswith("Title: "):
                    metadata["title"] = line[7:].strip()
                elif line.startswith("URL Source: "):
                    metadata["source_url"] = line[12:].strip()
                elif line.startswith("Published Time: "):
                    metadata["published_at"] = line[16:].strip()
                elif line.startswith("Markdown Content:"):
                    content_start = i + 1
                    break

            markdown_content = "\n".join(lines[content_start:]).strip()

            return markdown_content, metadata

    except httpx.HTTPError as e:
        raise RuntimeError(f"Failed to fetch URL: {e}")


def read_file_content(file_path: str) -> tuple[str, dict]:
    """Read content from local file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    metadata = {
        "file_path": str(path.absolute()),
        "file_name": path.name,
        "file_size": path.stat().st_size,
    }

    if ext == ".pdf":
        # Use pdftotext if available, otherwise try Jina for PDF URLs
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", file_path, "-"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return result.stdout, metadata
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: read raw text
        with open(path, "rb") as f:
            raw = f.read()
            # Try to extract text from PDF
            content = raw.decode("utf-8", errors="ignore")
            return content, metadata

    # Read as text
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    return content, metadata


def normalize_content(source: IngestSource) -> NormalizedContent:
    """Normalize any source to markdown."""
    now = datetime.now(timezone.utc).isoformat()

    if source.source_type == "url" and source.normalized_url:
        content, metadata = fetch_url_content(source.normalized_url)
        return NormalizedContent(
            title=metadata.get("title", "Untitled"),
            content=content,
            source_url=source.normalized_url,
            source_type="url",
            raw_metadata=metadata,
            extracted_at=now,
        )

    elif source.source_type == "x_thread" and source.normalized_url:
        content, metadata = fetch_url_content(source.normalized_url)
        # X threads often don't have good titles from Jina
        title = metadata.get("title", "")
        if not title or title in ("X", "Twitter"):
            # Extract first line as title
            first_line = content.split("\n")[0][:100] if content else "X Thread"
            title = f"X Thread: {first_line}"

        return NormalizedContent(
            title=title,
            content=content,
            source_url=source.normalized_url,
            source_type="x_thread",
            raw_metadata=metadata,
            extracted_at=now,
        )

    elif source.source_type == "gdoc" and source.normalized_url:
        # Convert to export URL for plain text
        doc_id_match = re.search(r"/d/([a-zA-Z0-9_-]+)", source.normalized_url)
        if doc_id_match:
            doc_id = doc_id_match.group(1)
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            content, metadata = fetch_url_content(export_url)
        else:
            content, metadata = fetch_url_content(source.normalized_url)

        return NormalizedContent(
            title=metadata.get("title", "Google Doc"),
            content=content,
            source_url=source.normalized_url,
            source_type="gdoc",
            raw_metadata=metadata,
            extracted_at=now,
        )

    elif source.file_path:
        content, metadata = read_file_content(source.file_path)
        # Extract title from first heading or filename
        title = Path(source.file_path).stem
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        return NormalizedContent(
            title=title,
            content=content,
            source_type=source.source_type,
            raw_metadata=metadata,
            extracted_at=now,
        )

    elif source.source_type == "raw_text":
        # Raw text input
        lines = source.original_input.split("\n")
        title = lines[0][:100] if lines else "Untitled"

        return NormalizedContent(
            title=title,
            content=source.original_input,
            source_type="raw_text",
            extracted_at=now,
        )

    raise ValueError(f"Unsupported source type: {source.source_type}")


# ---------------------------------------------------------------------------
# Stage 2: Content Triage (LLM)
# ---------------------------------------------------------------------------

def call_claude(messages: list[dict], system: str = "", max_tokens: int = 2000) -> str:
    """Call Claude API."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    payload = {
        "model": DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        # Extract text from response
        content = data.get("content", [])
        if content and isinstance(content, list):
            return content[0].get("text", "")
        return ""


def triage_content(normalized: NormalizedContent) -> TriagedContent:
    """Use LLM to triage content for relevance and quality."""

    system_prompt = """You are a knowledge triage system. Analyze the provided content and return a JSON object with:
{
    "relevance_score": 0.0-1.0 (how relevant to software development, AI, startups, or technology),
    "quality_score": 0.0-1.0 (information density, clarity, actionability),
    "entities": ["entity1", "entity2"] (key people, companies, technologies mentioned),
    "topics": ["topic1", "topic2"] (main topics covered),
    "key_insights": ["insight1", "insight2"] (2-5 key takeaways),
    "should_ingest": true/false (worth storing in knowledge base?),
    "rejection_reason": null or "reason" (if should_ingest is false)
}

Be selective. Only recommend ingestion for content that provides:
- Novel insights or perspectives
- Actionable information
- Important updates or announcements
- Unique technical knowledge

Reject content that is:
- Generic/common knowledge
- Low information density
- Primarily promotional without substance
- Duplicate of likely existing knowledge"""

    content_preview = normalized.content[:4000]  # Limit for API

    user_message = f"""Analyze this content for knowledge ingestion:

Title: {normalized.title}
Source: {normalized.source_url or 'local file'}
Type: {normalized.source_type}

Content:
{content_preview}"""

    try:
        response = call_claude(
            messages=[{"role": "user", "content": user_message}],
            system=system_prompt,
            max_tokens=1000,
        )

        # Parse JSON response
        # Find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
            return TriagedContent(
                relevance_score=float(data.get("relevance_score", 0.5)),
                quality_score=float(data.get("quality_score", 0.5)),
                entities=data.get("entities", []),
                topics=data.get("topics", []),
                key_insights=data.get("key_insights", []),
                should_ingest=data.get("should_ingest", True),
                rejection_reason=data.get("rejection_reason"),
            )
    except Exception as e:
        # Default to accepting on error
        return TriagedContent(
            relevance_score=0.5,
            quality_score=0.5,
            should_ingest=True,
        )

    return TriagedContent(relevance_score=0.5, quality_score=0.5, should_ingest=True)


# ---------------------------------------------------------------------------
# Stage 3: Research Expansion
# ---------------------------------------------------------------------------

def search_jina(query: str, num_results: int = 3) -> list[dict]:
    """Search using Jina for context expansion."""
    try:
        search_url = f"https://s.jina.ai/{query}"
        with httpx.Client(timeout=15.0) as client:
            response = client.get(search_url, headers={"Accept": "application/json"})
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])[:num_results]
    except Exception:
        pass
    return []


def find_related_entries(topics: list[str], entities: list[str]) -> list[dict]:
    """Find related entries in Onelist."""
    related = []

    # Search by topics and entities
    search_terms = topics[:3] + entities[:3]

    for term in search_terms:
        if not term:
            continue

        # Escape single quotes for SQL
        safe_term = term.replace("'", "''")

        try:
            result = subprocess.run(
                [
                    "psql", "-d", DATABASE, "-tAc",
                    f"""SELECT id, title, entry_type, metadata->>'plan_id' as plan_id
                        FROM entries
                        WHERE user_id = '{USER_ID}'
                        AND (title ILIKE '%{safe_term}%' OR metadata::text ILIKE '%{safe_term}%')
                        LIMIT 5"""
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            for line in result.stdout.strip().split("\n"):
                if line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        related.append({
                            "id": parts[0],
                            "title": parts[1],
                            "entry_type": parts[2],
                            "plan_id": parts[3] if len(parts) > 3 else None,
                            "matched_term": term,
                        })
        except Exception:
            pass

    # Deduplicate by id
    seen = set()
    unique = []
    for entry in related:
        if entry["id"] not in seen:
            seen.add(entry["id"])
            unique.append(entry)

    return unique[:10]


def expand_content(normalized: NormalizedContent, triaged: TriagedContent) -> ExpandedContent:
    """Expand content with research and cross-references."""

    # Search for related context
    search_queries = triaged.topics[:2] + triaged.entities[:2]
    related_searches = []

    for query in search_queries[:3]:
        if query:
            results = search_jina(query, num_results=2)
            for r in results:
                related_searches.append({
                    "query": query,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", "")[:200],
                })

    # Find existing related entries
    existing_entries = find_related_entries(triaged.topics, triaged.entities)

    return ExpandedContent(
        related_searches=related_searches,
        existing_entries=existing_entries,
    )


# ---------------------------------------------------------------------------
# Stage 4: Synthesis
# ---------------------------------------------------------------------------

def synthesize_report(
    normalized: NormalizedContent,
    triaged: TriagedContent,
    expanded: ExpandedContent,
) -> SynthesizedReport:
    """Synthesize final knowledge report."""

    system_prompt = """You are a knowledge synthesis system. Create a structured knowledge report from the provided content analysis.

Return a JSON object:
{
    "title": "Clear, descriptive title for this knowledge entry",
    "summary": "2-3 sentence summary of the core knowledge",
    "insights": ["insight1", "insight2", ...] (key learnings, max 5),
    "knowledge_claims": ["claim1", "claim2", ...] (factual assertions from the content, max 5),
    "implications": ["implication1", ...] (what this means for future work, max 3),
    "action_items": ["action1", ...] (concrete next steps if any, max 3),
    "tags": ["tag1", "tag2", ...] (categorization tags, max 5),
    "confidence": 0.0-1.0 (confidence in the extracted knowledge)
}

Focus on:
- Extracting actionable knowledge
- Identifying implications for ongoing work
- Connecting to existing knowledge where relevant
- Being specific rather than generic"""

    # Build context
    related_context = ""
    if expanded.existing_entries:
        related_context = "\n\nRelated existing entries:\n" + "\n".join([
            f"- {e['title']} ({e['entry_type']})"
            for e in expanded.existing_entries[:5]
        ])

    user_message = f"""Synthesize knowledge from this analysis:

Original Content Title: {normalized.title}
Source: {normalized.source_url or 'local'}
Type: {normalized.source_type}

Key Entities: {', '.join(triaged.entities[:5])}
Topics: {', '.join(triaged.topics[:5])}
Initial Insights: {'; '.join(triaged.key_insights[:3])}

Content (first 3000 chars):
{normalized.content[:3000]}
{related_context}"""

    try:
        response = call_claude(
            messages=[{"role": "user", "content": user_message}],
            system=system_prompt,
            max_tokens=1500,
        )

        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
            return SynthesizedReport(
                title=data.get("title", normalized.title),
                summary=data.get("summary", ""),
                insights=data.get("insights", triaged.key_insights),
                knowledge_claims=data.get("knowledge_claims", []),
                implications=data.get("implications", []),
                action_items=data.get("action_items", []),
                related_entries=[e["id"] for e in expanded.existing_entries],
                tags=data.get("tags", triaged.topics[:5]),
                source_url=normalized.source_url,
                confidence=float(data.get("confidence", 0.7)),
            )
    except Exception as e:
        pass

    # Fallback
    return SynthesizedReport(
        title=normalized.title,
        summary=normalized.content[:300],
        insights=triaged.key_insights,
        tags=triaged.topics[:5],
        source_url=normalized.source_url,
        confidence=0.5,
    )


# ---------------------------------------------------------------------------
# Stage 5: Knowledge Graph Integration
# ---------------------------------------------------------------------------

def generate_public_id() -> str:
    """Generate a nanoid-style public ID."""
    import random
    import string
    alphabet = string.ascii_letters + string.digits + "_-"
    return "".join(random.choices(alphabet, k=21))


def store_knowledge_entry(
    report: SynthesizedReport,
    normalized: NormalizedContent,
    triaged: TriagedContent,
) -> tuple[str, str]:
    """Store knowledge entry in Onelist."""

    entry_id = str(uuid.uuid4())
    public_id = generate_public_id()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Build metadata
    metadata = {
        "source_url": report.source_url,
        "source_type": normalized.source_type,
        "insights": report.insights,
        "knowledge_claims": report.knowledge_claims,
        "implications": report.implications,
        "action_items": report.action_items,
        "tags": report.tags,
        "entities": triaged.entities,
        "topics": triaged.topics,
        "relevance_score": triaged.relevance_score,
        "quality_score": triaged.quality_score,
        "confidence": report.confidence,
        "related_entry_ids": report.related_entries,
        "ingested_at": now,
    }

    # Escape for SQL
    title_escaped = report.title.replace("'", "''")
    metadata_json = json.dumps(metadata).replace("'", "''")

    # Insert entry
    insert_sql = f"""
        INSERT INTO entries (
            id, public_id, user_id, title, version, entry_type, source_type,
            public, metadata, inserted_at, updated_at
        ) VALUES (
            '{entry_id}',
            '{public_id}',
            '{USER_ID}',
            '{title_escaped}',
            1,
            'knowledge',
            'ingestion',
            false,
            '{metadata_json}'::jsonb,
            '{now}',
            '{now}'
        )
    """

    try:
        subprocess.run(
            ["psql", "-d", DATABASE, "-c", insert_sql],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to insert entry: {e.stderr}")

    # Store content as representation
    content_escaped = (report.summary + "\n\n" + normalized.content[:10000]).replace("'", "''")
    rep_id = str(uuid.uuid4())

    rep_sql = f"""
        INSERT INTO representations (
            id, entry_id, version, type, content, mime_type, encrypted, inserted_at, updated_at
        ) VALUES (
            '{rep_id}',
            '{entry_id}',
            1,
            'markdown',
            '{content_escaped}',
            'text/markdown',
            false,
            '{now}',
            '{now}'
        )
    """

    try:
        subprocess.run(
            ["psql", "-d", DATABASE, "-c", rep_sql],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except subprocess.CalledProcessError:
        pass  # Non-fatal

    return entry_id, public_id


def create_entry_links(entry_id: str, related_entry_ids: list[str]) -> list[str]:
    """Create bidirectional links to related entries."""
    created = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    for related_id in related_entry_ids[:10]:
        if not related_id:
            continue

        # Create link from new entry to related
        link_id = str(uuid.uuid4())
        link_sql = f"""
            INSERT INTO entry_links (
                id, source_entry_id, target_entry_id, link_type, metadata, inserted_at, updated_at
            ) VALUES (
                '{link_id}',
                '{entry_id}',
                '{related_id}',
                'related_to',
                '{{"source": "ingestion"}}'::jsonb,
                '{now}',
                '{now}'
            )
            ON CONFLICT DO NOTHING
        """

        try:
            subprocess.run(
                ["psql", "-d", DATABASE, "-c", link_sql],
                capture_output=True,
                timeout=5,
            )
            created.append(f"{entry_id} -> {related_id}")
        except Exception:
            pass

        # Create reverse link for bidirectional
        rev_link_id = str(uuid.uuid4())
        rev_link_sql = f"""
            INSERT INTO entry_links (
                id, source_entry_id, target_entry_id, link_type, metadata, inserted_at, updated_at
            ) VALUES (
                '{rev_link_id}',
                '{related_id}',
                '{entry_id}',
                'related_to',
                '{{"source": "ingestion", "direction": "reverse"}}'::jsonb,
                '{now}',
                '{now}'
            )
            ON CONFLICT DO NOTHING
        """

        try:
            subprocess.run(
                ["psql", "-d", DATABASE, "-c", rev_link_sql],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass

    return created


# ---------------------------------------------------------------------------
# Stage 6: Ripple Updates
# ---------------------------------------------------------------------------

def check_contradictions(report: SynthesizedReport, existing: list[dict]) -> list[dict]:
    """Check for potential contradictions with existing entries."""
    # This would use embeddings/semantic search in production
    # For now, return empty (no contradictions detected)
    return []


def flag_stale_entries(report: SynthesizedReport, existing: list[dict]) -> list[str]:
    """Flag entries that might be outdated by new knowledge."""
    # Placeholder for future implementation
    return []


# ---------------------------------------------------------------------------
# Stage 7: Auto-QCP
# ---------------------------------------------------------------------------

def generate_plans_from_insights(report: SynthesizedReport) -> list[dict]:
    """Generate plan suggestions from action items and implications."""
    suggestions = []

    for action in report.action_items:
        if action:
            suggestions.append({
                "type": "action_item",
                "title": action,
                "source": report.title,
                "priority": "medium",
            })

    for implication in report.implications:
        if implication and "should" in implication.lower():
            suggestions.append({
                "type": "implication",
                "title": implication,
                "source": report.title,
                "priority": "low",
            })

    return suggestions[:5]


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def ingest(
    input_source: str,
    skip_triage: bool = False,
    skip_expansion: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> IngestResult:
    """Run the full ingestion pipeline."""

    result = IngestResult(success=False)

    try:
        # Stage 1: Normalize
        if verbose:
            print(f"[1/7] Detecting source type...")
        source = detect_source_type(input_source)

        if verbose:
            print(f"[1/7] Normalizing {source.source_type} content...")
        normalized = normalize_content(source)

        if verbose:
            print(f"      Title: {normalized.title}")
            print(f"      Content length: {len(normalized.content)} chars")

        # Stage 2: Triage
        if skip_triage:
            triaged = TriagedContent(relevance_score=0.7, quality_score=0.7, should_ingest=True)
        else:
            if verbose:
                print(f"[2/7] Running LLM triage...")
            triaged = triage_content(normalized)

            if verbose:
                print(f"      Relevance: {triaged.relevance_score:.2f}")
                print(f"      Quality: {triaged.quality_score:.2f}")
                print(f"      Entities: {', '.join(triaged.entities[:5])}")
                print(f"      Topics: {', '.join(triaged.topics[:5])}")

        if not triaged.should_ingest:
            result.warnings.append(f"Content rejected: {triaged.rejection_reason}")
            if verbose:
                print(f"[!] Content rejected: {triaged.rejection_reason}")
            return result

        # Stage 3: Expand
        if skip_expansion:
            expanded = ExpandedContent()
        else:
            if verbose:
                print(f"[3/7] Expanding with research...")
            expanded = expand_content(normalized, triaged)

            if verbose:
                print(f"      Related searches: {len(expanded.related_searches)}")
                print(f"      Existing entries: {len(expanded.existing_entries)}")

        # Stage 4: Synthesize
        if verbose:
            print(f"[4/7] Synthesizing knowledge report...")
        report = synthesize_report(normalized, triaged, expanded)

        if verbose:
            print(f"      Insights: {len(report.insights)}")
            print(f"      Action items: {len(report.action_items)}")
            print(f"      Confidence: {report.confidence:.2f}")

        result.title = report.title

        if dry_run:
            if verbose:
                print(f"[DRY RUN] Would store entry: {report.title}")
                print(f"          Summary: {report.summary[:200]}...")
            result.success = True
            result.suggested_plans = generate_plans_from_insights(report)
            return result

        # Stage 5: Store
        if verbose:
            print(f"[5/7] Storing in knowledge graph...")
        entry_id, public_id = store_knowledge_entry(report, normalized, triaged)
        result.entry_id = entry_id
        result.public_id = public_id

        if verbose:
            print(f"      Entry ID: {entry_id}")
            print(f"      Public ID: {public_id}")

        # Create links
        if verbose:
            print(f"[5/7] Creating entry links...")
        created_links = create_entry_links(entry_id, report.related_entries)
        result.created_links = created_links

        if verbose:
            print(f"      Created {len(created_links)} links")

        # Stage 6: Ripple updates (placeholder)
        if verbose:
            print(f"[6/7] Checking for ripple effects...")
        contradictions = check_contradictions(report, expanded.existing_entries)
        if contradictions:
            result.warnings.append(f"Potential contradictions detected: {len(contradictions)}")

        # Stage 7: Auto-QCP
        if verbose:
            print(f"[7/7] Generating plan suggestions...")
        result.suggested_plans = generate_plans_from_insights(report)

        if verbose and result.suggested_plans:
            print(f"      Suggested plans: {len(result.suggested_plans)}")
            for plan in result.suggested_plans:
                print(f"        - {plan['title'][:60]}...")

        result.success = True

    except Exception as e:
        result.errors.append(str(e))
        if verbose:
            print(f"[ERROR] {e}")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="crux-ingest: Universal Ingestion Pipeline for knowledge extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  crux ingest https://example.com/article
  crux ingest https://x.com/user/status/123456
  crux ingest ./document.md
  crux ingest ./report.pdf
  crux ingest "https://docs.google.com/document/d/..."

Supported sources:
  - Web URLs (articles, documentation)
  - X/Twitter threads
  - Markdown files
  - HTML files
  - PDF files
  - Google Docs
""",
    )

    parser.add_argument(
        "source",
        help="URL or file path to ingest",
    )

    parser.add_argument(
        "--skip-triage",
        action="store_true",
        help="Skip LLM triage (accept all content)",
    )

    parser.add_argument(
        "--skip-expansion",
        action="store_true",
        help="Skip research expansion (faster, less context)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze without storing to database",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    result = ingest(
        input_source=args.source,
        skip_triage=args.skip_triage,
        skip_expansion=args.skip_expansion,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    # Output result
    if result.success:
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Ingestion successful!")
        print(f"  Title: {result.title}")
        if result.entry_id:
            print(f"  Entry ID: {result.entry_id}")
            print(f"  Public ID: {result.public_id}")
        if result.created_links:
            print(f"  Links created: {len(result.created_links)}")
        if result.suggested_plans:
            print(f"\n  Suggested plans:")
            for plan in result.suggested_plans:
                print(f"    - [{plan['priority']}] {plan['title']}")
    else:
        print(f"\nIngestion failed!")
        for error in result.errors:
            print(f"  Error: {error}")
        for warning in result.warnings:
            print(f"  Warning: {warning}")
        sys.exit(1)

    if result.warnings:
        print(f"\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
