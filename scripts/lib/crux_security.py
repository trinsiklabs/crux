"""Security utilities for Crux file system operations.

This module provides secure path validation, atomic file operations, and safe
subprocess execution to prevent path traversal, TOCTOU race conditions, and
other file system vulnerabilities.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path


# Pattern for safe filenames: alphanumeric, underscore, hyphen only
SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


def validate_safe_filename(name: str) -> bool:
    """Check if a filename contains only safe characters [a-zA-Z0-9_-].

    Args:
        name: The filename (without extension) to validate.

    Returns:
        True if the filename is safe, False otherwise.
    """
    return bool(SAFE_FILENAME_PATTERN.match(name))


def validate_path_within_base(path: Path, base: Path) -> bool:
    """Verify that a resolved path stays within a base directory.

    This prevents path traversal attacks via symlinks or .. components.

    Args:
        path: The path to validate (will be resolved).
        base: The base directory that path must stay within.

    Returns:
        True if the resolved path is within base, False otherwise.
    """
    try:
        resolved = path.resolve()
        base_resolved = base.resolve()
        # Use os.path.commonpath to handle edge cases
        return os.path.commonpath([resolved, base_resolved]) == str(base_resolved)
    except (ValueError, OSError):
        return False


def safe_glob_files(directory: Path, pattern: str) -> list[Path]:
    """Glob files within a directory, filtering out symlinks to outside directories.

    Args:
        directory: The base directory to glob within.
        pattern: The glob pattern (e.g., "*.md").

    Returns:
        List of Path objects that are regular files within the directory.
    """
    if not directory.is_dir():
        return []

    result: list[Path] = []
    base_resolved = directory.resolve()

    for match in directory.glob(pattern):
        # Skip symlinks entirely - they could point anywhere
        if match.is_symlink():
            continue
        # Verify the resolved path stays within the base directory
        if not validate_path_within_base(match, directory):
            continue
        # Only include regular files
        if match.is_file():
            result.append(match)

    return result


def atomic_symlink(source: str, target: str) -> None:
    """Create a symlink atomically using temp file + rename pattern.

    This prevents TOCTOU race conditions by creating the symlink with a
    temporary name and then atomically renaming it to the target.

    Args:
        source: The source path the symlink will point to.
        target: The target path where the symlink will be created.
    """
    target_dir = os.path.dirname(target)
    if target_dir:
        os.makedirs(target_dir, mode=0o700, exist_ok=True)

    # Create temp symlink in the same directory
    fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix='.crux_symlink_')
    os.close(fd)
    os.unlink(temp_path)  # Remove the temp file, we just want the name

    try:
        os.symlink(source, temp_path)
        os.rename(temp_path, target)  # Atomic on POSIX
    except OSError:
        # Clean up temp symlink if rename fails
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def secure_makedirs(path: str, mode: int = 0o700) -> None:
    """Create directories with secure permissions.

    Args:
        path: The directory path to create.
        mode: The permissions mode (default: 0o700 - owner only).
    """
    os.makedirs(path, mode=mode, exist_ok=True)


def secure_write_file(path: str, content: str, mode: int = 0o600) -> None:
    """Write content to a file with secure permissions.

    Uses atomic write pattern (write to temp, then rename) to prevent
    partial writes and ensure secure permissions.

    Args:
        path: The file path to write to.
        content: The content to write.
        mode: The file permissions mode (default: 0o600 - owner read/write only).
    """
    parent_dir = os.path.dirname(path)
    if parent_dir:
        secure_makedirs(parent_dir)

    # Write to temp file first
    fd, temp_path = tempfile.mkstemp(dir=parent_dir, prefix='.crux_write_')
    try:
        os.fchmod(fd, mode)
        os.write(fd, content.encode('utf-8'))
        os.close(fd)
        os.rename(temp_path, path)  # Atomic on POSIX
    except Exception:
        os.close(fd) if fd else None
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def git_env_disable_hooks() -> dict[str, str]:
    """Return environment variables that disable git hooks.

    This prevents arbitrary code execution when running git in untrusted
    directories.

    Returns:
        Dictionary of environment variables to pass to subprocess.
    """
    env = os.environ.copy()
    # Disable hooks
    env['GIT_CONFIG_NOSYSTEM'] = '1'
    env['GIT_TERMINAL_PROMPT'] = '0'
    # Disable config that could run arbitrary commands
    env['GIT_ASKPASS'] = '/bin/true'
    env['SSH_ASKPASS'] = '/bin/true'
    return env


def validate_and_canonicalize_dir(path: str) -> str | None:
    """Validate and canonicalize a directory path.

    Args:
        path: The directory path to validate.

    Returns:
        The canonicalized absolute path if valid, None otherwise.
    """
    try:
        canonical = os.path.realpath(path)
        if os.path.isdir(canonical):
            return canonical
    except (OSError, ValueError):
        pass
    return None
