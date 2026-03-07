"""Extract correction patterns from session JSONL logs and cluster into knowledge candidates.

Security improvements (PLAN-166):
- Input validation with max field sizes (10KB per string)
- Bounded file reading to prevent memory exhaustion
- Structured logging for audit trail
"""

import json
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Configure structured logging
_logger = logging.getLogger("crux.extract_corrections")

# Maximum field sizes (bytes)
_MAX_FIELD_SIZE = 10240  # 10KB per string field
_MAX_LINE_LENGTH = 102400  # 100KB per line
_MAX_ENTRIES_PER_FILE = 10000
_MAX_FILES_TO_SCAN = 100


def _truncate_field(value: str, max_length: int = _MAX_FIELD_SIZE) -> str:
    """Truncate a field to max length."""
    if len(value) > max_length:
        return value[:max_length] + "...[truncated]"
    return value


def _validate_string_field(value, field_name: str, max_length: int = _MAX_FIELD_SIZE) -> str:
    """Validate and sanitize a string field."""
    if value is None:
        return ""
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            _logger.warning("Cannot convert %s to string", field_name)
            return ""
    return _truncate_field(value, max_length)


@dataclass
class CorrectionEntry:
    timestamp: str
    category: str
    original: str
    corrected: str
    pattern: str
    mode: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "category": self.category,
            "original": self.original,
            "corrected": self.corrected,
            "pattern": self.pattern,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CorrectionEntry":
        """Create a CorrectionEntry from a dict with validation."""
        return cls(
            timestamp=_validate_string_field(data.get("timestamp", ""), "timestamp", 100),
            category=_validate_string_field(data.get("category", "unknown"), "category", 500),
            original=_validate_string_field(data.get("original", ""), "original"),
            corrected=_validate_string_field(data.get("corrected", ""), "corrected"),
            pattern=_validate_string_field(data.get("pattern", ""), "pattern"),
            mode=_validate_string_field(data.get("mode", "unknown"), "mode", 500),
        )


@dataclass
class CorrectionCluster:
    category: str
    mode: str
    entries: list[CorrectionEntry] = field(default_factory=list)
    count: int = 0

    @property
    def key(self) -> str:
        return f"{self.category}:{self.mode}"

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "mode": self.mode,
            "count": self.count,
            "entries": [e.to_dict() for e in self.entries[:5]],  # Keep top 5 examples
        }


def parse_reflections_file(file_path: str) -> list[CorrectionEntry]:
    """Parse a JSONL reflections file into CorrectionEntry objects.

    Security features:
    - Line length validation
    - Entry count limits
    - Field size validation
    """
    entries = []
    line_number = 0
    skipped_count = 0

    try:
        with open(file_path, "r") as f:
            for line in f:
                line_number += 1

                # Check entry limit
                if len(entries) >= _MAX_ENTRIES_PER_FILE:
                    _logger.warning(
                        "Hit max entries limit (%d) in %s, stopping",
                        _MAX_ENTRIES_PER_FILE, file_path
                    )
                    break

                line = line.strip()
                if not line:
                    continue

                # Check line length
                if len(line) > _MAX_LINE_LENGTH:
                    _logger.warning(
                        "Skipping oversized line %d in %s (%d bytes)",
                        line_number, file_path, len(line)
                    )
                    skipped_count += 1
                    continue

                try:
                    data = json.loads(line)

                    if not isinstance(data, dict):
                        skipped_count += 1
                        continue

                    if data.get("type") == "self-correction":
                        entries.append(CorrectionEntry.from_dict(data))

                except json.JSONDecodeError:
                    skipped_count += 1
                    continue

    except FileNotFoundError:
        pass
    except (OSError, IOError) as e:
        _logger.warning("Cannot read file %s: %s", file_path, str(e)[:50])

    if skipped_count > 0:
        _logger.info(
            "Parsed %s: %d entries, %d skipped",
            file_path, len(entries), skipped_count
        )

    return entries


def scan_reflections_dir(reflections_dir: str) -> list[CorrectionEntry]:
    """Scan all .jsonl files in the reflections directory.

    Security features:
    - File count limit
    - Total entry limit
    """
    all_entries = []
    files_scanned = 0

    try:
        files = sorted(os.listdir(reflections_dir))
    except FileNotFoundError:
        return []
    except (OSError, IOError) as e:
        _logger.warning("Cannot list directory %s: %s", reflections_dir, str(e)[:50])
        return []

    for filename in files:
        if not filename.endswith(".jsonl"):
            continue

        # Check file limit
        if files_scanned >= _MAX_FILES_TO_SCAN:
            _logger.warning(
                "Hit max files limit (%d), stopping scan",
                _MAX_FILES_TO_SCAN
            )
            break

        filepath = os.path.join(reflections_dir, filename)

        # Skip if not a regular file
        if not os.path.isfile(filepath):
            continue

        entries = parse_reflections_file(filepath)
        all_entries.extend(entries)
        files_scanned += 1

        # Check total entries limit
        if len(all_entries) >= _MAX_ENTRIES_PER_FILE * 10:
            _logger.warning(
                "Hit total entries limit (%d), stopping scan",
                _MAX_ENTRIES_PER_FILE * 10
            )
            break

    _logger.info(
        "Scanned %d files, found %d corrections",
        files_scanned, len(all_entries)
    )

    return all_entries


def cluster_corrections(entries: list[CorrectionEntry]) -> list[CorrectionCluster]:
    """Cluster corrections by category and mode."""
    clusters: dict[str, CorrectionCluster] = {}

    for entry in entries:
        key = f"{entry.category}:{entry.mode}"
        if key not in clusters:
            clusters[key] = CorrectionCluster(
                category=entry.category,
                mode=entry.mode,
            )
        cluster = clusters[key]
        cluster.entries.append(entry)
        cluster.count += 1

    # Sort by count descending
    return sorted(clusters.values(), key=lambda c: c.count, reverse=True)


def generate_knowledge_candidate(cluster: CorrectionCluster) -> str:
    """Generate a knowledge entry markdown from a correction cluster."""
    examples = cluster.entries[:3]
    example_lines = []
    for e in examples:
        # Truncate for display
        original = e.original[:200] + "..." if len(e.original) > 200 else e.original
        corrected = e.corrected[:200] + "..." if len(e.corrected) > 200 else e.corrected
        example_lines.append(f"- Original: {original}")
        example_lines.append(f"  Corrected: {corrected}")

    return "\n".join([
        f"# Correction Pattern: {cluster.category} in {cluster.mode}",
        "",
        f"**Category**: {cluster.category}",
        f"**Mode**: {cluster.mode}",
        f"**Occurrences**: {cluster.count}",
        "",
        "## Examples",
        "",
        *example_lines,
        "",
        f"Tags: {cluster.category}, {cluster.mode}, correction",
    ])


def extract_corrections(
    reflections_dir: Optional[str] = None,
    min_cluster_size: int = 2,
) -> dict:
    """Main extraction pipeline: scan, cluster, generate candidates.

    Args:
        reflections_dir: Directory containing reflection JSONL files
        min_cluster_size: Minimum cluster size to be considered significant

    Returns:
        Dictionary with extraction results
    """
    if reflections_dir is None:
        reflections_dir = os.path.join(
            os.environ.get("HOME", ""),
            ".crux", "corrections",
        )

    _logger.info("Starting correction extraction from %s", reflections_dir)

    entries = scan_reflections_dir(reflections_dir)
    clusters = cluster_corrections(entries)

    # Filter to clusters with enough occurrences
    significant = [c for c in clusters if c.count >= min_cluster_size]

    candidates = []
    for cluster in significant:
        candidates.append({
            "cluster": cluster.to_dict(),
            "knowledge_entry": generate_knowledge_candidate(cluster),
        })

    result = {
        "total_entries": len(entries),
        "total_clusters": len(clusters),
        "significant_clusters": len(significant),
        "candidates": candidates,
    }

    _logger.info(
        "Extraction complete: %d entries, %d clusters, %d significant",
        len(entries), len(clusters), len(significant)
    )

    return result


def main() -> None:
    """CLI entry point."""
    import sys

    # Configure logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    reflections_dir = sys.argv[1] if len(sys.argv) > 1 else None
    min_size = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    result = extract_corrections(reflections_dir, min_size)

    if result["significant_clusters"] == 0:
        print("No significant correction patterns found.")
        sys.exit(0)

    print(f"Found {result['total_entries']} corrections in {result['total_clusters']} clusters.")
    print(f"{result['significant_clusters']} clusters meet threshold (>= {min_size}).\n")

    for candidate in result["candidates"]:
        print("---")
        print(candidate["knowledge_entry"])
        print()


if __name__ == "__main__":  # pragma: no cover
    main()
