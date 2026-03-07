"""Tool-agnostic path resolution for Crux.

All paths funnel through this module. No other module should hardcode
.opencode, .claude, .cursor, etc. — they call get_project_paths() or
get_user_paths() and use the returned object.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

CRUX_DIR_NAME = ".crux"


@dataclass(frozen=True)
class UserPaths:
    """Paths rooted at ~/.crux/"""
    root: str

    @property
    def knowledge(self) -> str:
        return os.path.join(self.root, "knowledge")

    @property
    def knowledge_shared(self) -> str:
        return os.path.join(self.root, "knowledge", "shared")

    @property
    def knowledge_by_mode(self) -> str:
        return os.path.join(self.root, "knowledge", "by-mode")

    @property
    def modes(self) -> str:
        return os.path.join(self.root, "modes")

    @property
    def corrections(self) -> str:
        return os.path.join(self.root, "corrections")

    @property
    def analytics(self) -> str:
        return os.path.join(self.root, "analytics")

    @property
    def analytics_digests(self) -> str:
        return os.path.join(self.root, "analytics", "digests")

    @property
    def templates(self) -> str:
        return os.path.join(self.root, "templates")

    @property
    def scripts_lib(self) -> str:
        return os.path.join(self.root, "scripts", "lib")

    @property
    def config_file(self) -> str:
        return os.path.join(self.root, "config.json")

    @property
    def models(self) -> str:
        return os.path.join(self.root, "models")

    @property
    def models_registry(self) -> str:
        return os.path.join(self.root, "models", "registry.json")

    @property
    def adapters(self) -> str:
        return os.path.join(self.root, "adapters")


@dataclass(frozen=True)
class ProjectPaths:
    """Paths rooted at <project>/.crux/"""
    root: str

    @property
    def knowledge(self) -> str:
        return os.path.join(self.root, "knowledge")

    @property
    def knowledge_by_mode(self) -> str:
        return os.path.join(self.root, "knowledge", "by-mode")

    @property
    def corrections(self) -> str:
        return os.path.join(self.root, "corrections")

    @property
    def corrections_file(self) -> str:
        return os.path.join(self.root, "corrections", "corrections.jsonl")

    @property
    def sessions(self) -> str:
        return os.path.join(self.root, "sessions")

    @property
    def session_state(self) -> str:
        return os.path.join(self.root, "sessions", "state.json")

    @property
    def handoff(self) -> str:
        return os.path.join(self.root, "sessions", "handoff.md")

    @property
    def sessions_history(self) -> str:
        return os.path.join(self.root, "sessions", "history")

    @property
    def scripts(self) -> str:
        return os.path.join(self.root, "scripts")

    @property
    def scripts_lib(self) -> str:
        return os.path.join(self.root, "scripts", "lib")

    @property
    def scripts_session(self) -> str:
        return os.path.join(self.root, "scripts", "session")

    @property
    def scripts_archive(self) -> str:
        return os.path.join(self.root, "scripts", "archive")

    @property
    def scripts_templates(self) -> str:
        return os.path.join(self.root, "scripts", "templates")

    @property
    def context(self) -> str:
        return os.path.join(self.root, "context")

    @property
    def project_md(self) -> str:
        return os.path.join(self.root, "context", "PROJECT.md")

    @property
    def bip(self) -> str:
        return os.path.join(self.root, "bip")

    @property
    def bip_drafts(self) -> str:
        return os.path.join(self.root, "bip", "drafts")

    @property
    def bip_config(self) -> str:
        return os.path.join(self.root, "bip", "config.json")

    @property
    def bip_state(self) -> str:
        return os.path.join(self.root, "bip", "state.json")

    @property
    def bip_history(self) -> str:
        return os.path.join(self.root, "bip", "history.jsonl")

    @property
    def config_file(self) -> str:
        return os.path.join(self.root, "project.json")

    @property
    def models(self) -> str:
        return os.path.join(self.root, "models")

    @property
    def models_registry(self) -> str:
        return os.path.join(self.root, "models", "registry.json")


def get_crux_repo() -> str:
    """Return the absolute path to the Crux repo root."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_crux_python() -> str:
    """Return the Python executable for running Crux scripts.

    Prefers the venv Python at <repo>/.venv/bin/python if it exists (needed on
    Linux where the system Python is externally managed). Falls back to the
    current interpreter.
    """
    import sys
    repo = get_crux_repo()
    venv_python = os.path.join(repo, ".venv", "bin", "python")
    if os.path.isfile(venv_python):
        return venv_python
    return sys.executable


def get_user_paths(home: str | None = None) -> UserPaths:
    """Get user-level Crux paths (~/.crux/)."""
    if home is None:
        home = os.environ.get("HOME", "")
    return UserPaths(root=os.path.join(home, CRUX_DIR_NAME))


def get_project_paths(project_dir: str | None = None) -> ProjectPaths:
    """Get project-level Crux paths (<project>/.crux/)."""
    if project_dir is None:
        project_dir = os.getcwd()
    return ProjectPaths(root=os.path.join(project_dir, CRUX_DIR_NAME))


class CruxPaths:
    """Combined project + user paths with convenience methods."""

    def __init__(self, project_dir: str | None = None, home: str | None = None):
        self.project = get_project_paths(project_dir)
        self.user = get_user_paths(home)

    def knowledge_search_dirs(self, mode: str | None = None) -> list[str]:
        """Return knowledge directories in priority order (most specific first)."""
        dirs: list[str] = []
        if mode:
            dirs.append(os.path.join(self.project.knowledge_by_mode, mode))
            dirs.append(os.path.join(self.user.knowledge_by_mode, mode))
        dirs.append(self.project.knowledge)
        dirs.append(self.user.knowledge)
        dirs.append(self.user.knowledge_shared)
        return dirs
