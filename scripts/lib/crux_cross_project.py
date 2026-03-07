"""Cross-project aggregation — analytics across all Crux-enabled projects.

Discovers projects, aggregates digests and corrections, and generates
user-level insights spanning multiple codebases.

Security improvements (PLAN-166):
- Path traversal protection in project registration
- Bounded directory scanning with max depth
- Atomic file writes for registry
- Logging for skipped/corrupt entries
- Strict mode option for JSON parsing
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Configure structured logging
_logger = logging.getLogger("crux.cross_project")

# Default directories to scan for projects
_DEFAULT_SCAN_DIRS = ["", "projects", "personal", "work", "src", "dev"]

# Maximum directory scan depth to prevent unbounded recursion
_MAX_SCAN_DEPTH = 3

# Maximum number of projects to track
_MAX_PROJECTS = 100

# Maximum file size to read (10MB)
_MAX_FILE_SIZE = 10 * 1024 * 1024


def _registry_path(home: str) -> str:
    return os.path.join(home, ".crux", "projects.json")


def _is_safe_path(path: str, home: str) -> bool:
    """Validate that a path is within the user's home directory.

    Prevents path traversal attacks by ensuring registered projects
    are within allowed boundaries.
    """
    try:
        # Resolve to absolute path and normalize
        resolved = os.path.realpath(os.path.abspath(path))
        home_resolved = os.path.realpath(os.path.abspath(home))

        # Check if path is within home directory
        return resolved.startswith(home_resolved + os.sep) or resolved == home_resolved
    except (OSError, ValueError):
        return False


def _load_registry(home: str) -> list[str]:
    """Load project registry with validation."""
    path = _registry_path(home)
    try:
        # Check file size before loading
        file_size = os.path.getsize(path)
        if file_size > _MAX_FILE_SIZE:
            _logger.error("Registry file too large (%d bytes), refusing to load", file_size)
            return []

        with open(path) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            _logger.warning("Invalid registry format, expected dict")
            return []

        projects = data.get("projects", [])

        if not isinstance(projects, list):
            _logger.warning("Invalid projects format, expected list")
            return []

        # Validate each project path
        valid_projects = []
        for p in projects:
            if isinstance(p, str) and _is_safe_path(p, home):
                valid_projects.append(p)
            else:
                _logger.warning("Skipping invalid or unsafe project path: %s", str(p)[:100])

        return valid_projects

    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        _logger.error("Corrupt registry file at %s: %s", path, str(e)[:100])
        return []


def _save_registry(home: str, projects: list[str]) -> None:
    """Save project registry atomically."""
    path = _registry_path(home)
    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)

    # Validate all projects before saving
    valid_projects = [p for p in projects if _is_safe_path(p, home)]

    if len(valid_projects) != len(projects):
        _logger.warning(
            "Filtered %d unsafe paths from registry",
            len(projects) - len(valid_projects)
        )

    # Write atomically
    fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"projects": valid_projects}, f, indent=2)
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def discover_projects(home: str, max_depth: int = _MAX_SCAN_DEPTH, timeout_seconds: int = 30) -> list[str]:
    """Scan common locations for directories containing .crux/.

    Also includes any projects from the registry. Returns deduplicated,
    sorted list of project paths.

    Security improvements:
    - Bounded scan depth to prevent unbounded directory walking
    - Path validation to ensure all paths are within home
    - Project count limit to prevent memory exhaustion
    """
    import time

    start_time = time.time()
    found: set[str] = set()

    # Check registry first
    for p in _load_registry(home):
        if os.path.isdir(os.path.join(p, ".crux")):
            found.add(p)
            if len(found) >= _MAX_PROJECTS:
                _logger.warning("Hit max projects limit (%d)", _MAX_PROJECTS)
                return sorted(found)

    # Scan common directories with depth limit
    for subdir in _DEFAULT_SCAN_DIRS:
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            _logger.warning("Project discovery timed out after %d seconds", timeout_seconds)
            break

        scan_root = os.path.join(home, subdir) if subdir else home
        if not os.path.isdir(scan_root):
            continue

        # Validate scan root is within home
        if not _is_safe_path(scan_root, home):
            continue

        try:
            # Bounded directory walk
            found.update(_scan_directory_bounded(scan_root, home, max_depth, found))

            if len(found) >= _MAX_PROJECTS:
                _logger.warning("Hit max projects limit (%d)", _MAX_PROJECTS)
                break

        except PermissionError:
            continue

    return sorted(found)


def _scan_directory_bounded(
    root: str,
    home: str,
    max_depth: int,
    already_found: set[str]
) -> set[str]:
    """Scan a directory with bounded depth.

    Only descends to max_depth levels to prevent unbounded recursion.
    """
    found: set[str] = set()

    if max_depth <= 0:
        return found

    try:
        for entry in os.listdir(root):
            # Skip hidden directories except .crux
            if entry.startswith('.') and entry != '.crux':
                continue

            full = os.path.join(root, entry)

            # Validate path safety
            if not _is_safe_path(full, home):
                continue

            if not os.path.isdir(full):
                continue

            # Check if this directory has .crux
            crux_dir = os.path.join(full, ".crux")
            if os.path.isdir(crux_dir):
                found.add(full)
                if len(found) + len(already_found) >= _MAX_PROJECTS:
                    return found
            elif max_depth > 1:
                # Recursively scan, but don't descend into .crux directories
                found.update(_scan_directory_bounded(
                    full, home, max_depth - 1, already_found | found
                ))

    except (PermissionError, OSError) as e:
        _logger.debug("Cannot scan %s: %s", root, str(e)[:50])

    return found


def register_project(project_dir: str, home: str) -> dict:
    """Add a project to the registry.

    Validates that the project path is within the home directory
    to prevent path traversal attacks.
    """
    project_dir = os.path.abspath(project_dir)

    # Security: validate path is within home directory
    if not _is_safe_path(project_dir, home):
        _logger.warning("Rejected project registration outside home: %s", project_dir[:100])
        return {
            "registered": False,
            "reason": "path_outside_home_directory",
            "error": "Project path must be within home directory",
        }

    # Validate project directory exists
    if not os.path.isdir(project_dir):
        return {
            "registered": False,
            "reason": "directory_not_found",
        }

    projects = _load_registry(home)

    # Check project limit
    if len(projects) >= _MAX_PROJECTS:
        return {
            "registered": False,
            "reason": "max_projects_reached",
            "limit": _MAX_PROJECTS,
        }

    if project_dir in projects:
        return {"registered": False, "reason": "already registered", "projects": projects}

    projects.append(project_dir)
    _save_registry(home, projects)
    _logger.info("Registered project: %s", project_dir)

    return {"registered": True, "project": project_dir, "total_projects": len(projects)}


def unregister_project(project_dir: str, home: str) -> dict:
    """Remove a project from the registry."""
    project_dir = os.path.abspath(project_dir)
    projects = _load_registry(home)
    if project_dir not in projects:
        return {"unregistered": False, "reason": "not in registry"}
    projects.remove(project_dir)
    _save_registry(home, projects)
    _logger.info("Unregistered project: %s", project_dir)
    return {"unregistered": True, "project": project_dir, "total_projects": len(projects)}


def _count_interactions_for_date(project_dir: str, date_str: str) -> int:
    int_file = os.path.join(project_dir, ".crux", "analytics", "interactions", f"{date_str}.jsonl")
    if not os.path.exists(int_file):
        return 0
    count = 0
    try:
        with open(int_file) as f:
            for line in f:
                if line.strip():
                    count += 1
    except (OSError, IOError) as e:
        _logger.debug("Cannot read interactions file: %s", str(e)[:50])
    return count


def _count_corrections(project_dir: str) -> int:
    corr_file = os.path.join(project_dir, ".crux", "corrections", "corrections.jsonl")
    if not os.path.exists(corr_file):
        return 0
    count = 0
    try:
        with open(corr_file) as f:
            for line in f:
                if line.strip():
                    count += 1
    except (OSError, IOError) as e:
        _logger.debug("Cannot read corrections file: %s", str(e)[:50])
    return count


def _read_corrections(project_dir: str, strict: bool = False) -> list[dict]:
    """Read corrections file with validation and logging.

    Args:
        project_dir: Project directory path
        strict: If True, raise on corrupt entries instead of skipping

    Returns:
        List of valid correction entries
    """
    corr_file = os.path.join(project_dir, ".crux", "corrections", "corrections.jsonl")
    entries: list[dict] = []

    if not os.path.exists(corr_file):
        return entries

    skipped_count = 0
    line_number = 0

    try:
        with open(corr_file) as f:
            for line in f:
                line_number += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if not isinstance(entry, dict):
                        skipped_count += 1
                        if strict:
                            raise ValueError(f"Line {line_number}: expected dict, got {type(entry).__name__}")
                        continue
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    skipped_count += 1
                    _logger.debug(
                        "Skipped corrupt entry at line %d in %s: %s",
                        line_number, corr_file, str(e)[:50]
                    )
                    if strict:
                        raise ValueError(f"Line {line_number}: invalid JSON") from e

    except (OSError, IOError) as e:
        _logger.warning("Cannot read corrections file %s: %s", corr_file, str(e)[:50])

    if skipped_count > 0:
        _logger.info(
            "Skipped %d corrupt entries in %s (read %d valid)",
            skipped_count, corr_file, len(entries)
        )

    return entries


def _get_active_mode(project_dir: str) -> str | None:
    state_file = os.path.join(project_dir, ".crux", "sessions", "state.json")
    try:
        with open(state_file) as f:
            data = json.load(f)
        return data.get("active_mode")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def aggregate_digests(home: str, date_str: str | None = None) -> dict:
    """Merge analytics from all registered projects for a given date."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    projects = discover_projects(home)
    total_interactions = 0
    total_corrections = 0
    modes_used: Counter[str] = Counter()
    project_summaries: list[dict] = []

    for proj in projects:
        interactions = _count_interactions_for_date(proj, date_str)
        corrections = _count_corrections(proj)
        mode = _get_active_mode(proj)

        total_interactions += interactions
        total_corrections += corrections
        if mode:
            modes_used[mode] += 1

        project_summaries.append({
            "project": proj,
            "interactions": interactions,
            "corrections": corrections,
            "active_mode": mode,
        })

    return {
        "date": date_str,
        "total_projects": len(projects),
        "total_interactions": total_interactions,
        "total_corrections": total_corrections,
        "modes_used": dict(modes_used),
        "projects": project_summaries,
    }


def aggregate_corrections(home: str, strict: bool = False) -> dict:
    """Find correction patterns that appear across multiple projects.

    Args:
        home: Home directory path
        strict: If True, fail on corrupt entries instead of skipping
    """
    projects = discover_projects(home)
    # Track category counts per project
    category_projects: dict[str, set[str]] = {}
    category_counts: Counter[str] = Counter()

    for proj in projects:
        corrections = _read_corrections(proj, strict=strict)
        proj_categories: set[str] = set()
        for corr in corrections:
            cat = corr.get("category", "unknown")
            category_counts[cat] += 1
            proj_categories.add(cat)
        for cat in proj_categories:
            if cat not in category_projects:
                category_projects[cat] = set()
            category_projects[cat].add(proj)

    # Cross-project patterns: categories appearing in 2+ projects
    cross_project: list[dict] = []
    for cat, projs in category_projects.items():
        cross_project.append({
            "category": cat,
            "project_count": len(projs),
            "total_occurrences": category_counts[cat],
            "cross_project": len(projs) > 1,
        })
    cross_project.sort(key=lambda x: (-x["project_count"], -x["total_occurrences"]))

    return {
        "total_projects_scanned": len(projects),
        "patterns": cross_project,
        "cross_project_patterns": [p for p in cross_project if p["cross_project"]],
    }


def generate_user_digest(home: str, date_str: str | None = None) -> dict:
    """Generate a user-level digest spanning all projects."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    digest_data = aggregate_digests(home, date_str)
    correction_data = aggregate_corrections(home)

    # Write to user-level digest directory
    digest_dir = os.path.join(home, ".crux", "analytics", "digests")
    os.makedirs(digest_dir, exist_ok=True)

    lines = [
        f"# User Digest: {date_str}",
        "",
        "## Summary",
        f"- Projects: {digest_data['total_projects']}",
        f"- Total Interactions: {digest_data['total_interactions']}",
        f"- Total Corrections: {digest_data['total_corrections']}",
        "",
    ]

    if digest_data["modes_used"]:
        lines.extend(["## Modes Used Across Projects", ""])
        for mode, count in sorted(digest_data["modes_used"].items(), key=lambda x: -x[1]):
            lines.append(f"- {mode}: {count} project(s)")
        lines.append("")

    if correction_data["cross_project_patterns"]:
        lines.extend(["## Cross-Project Correction Patterns", ""])
        for p in correction_data["cross_project_patterns"]:
            lines.append(f"- {p['category']}: {p['total_occurrences']} occurrences across {p['project_count']} projects")
        lines.append("")

    if digest_data["projects"]:
        lines.extend(["## Per-Project Breakdown", ""])
        for proj in digest_data["projects"]:
            name = os.path.basename(proj["project"])
            lines.append(f"### {name}")
            lines.append(f"- Interactions: {proj['interactions']}")
            lines.append(f"- Corrections: {proj['corrections']}")
            if proj["active_mode"]:
                lines.append(f"- Active Mode: {proj['active_mode']}")
            lines.append("")

    content = "\n".join(lines)
    output_path = os.path.join(digest_dir, f"{date_str}.md")

    # Write atomically
    fd, temp_path = tempfile.mkstemp(dir=digest_dir, suffix=".md.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(temp_path, output_path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise

    return {
        "date": date_str,
        "output_path": output_path,
        "digest": digest_data,
        "corrections": correction_data,
        "content": content,
    }
