"""External MCP server registry — configure once, use everywhere.

Stores external MCP server configurations in .crux/mcp-servers.json.
Any tool connected to Crux gets access to all registered servers.

Security: servers require explicit registration (no auto-discovery),
CRUX_HOME/session state never forwarded, timeout enforced.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict

# Environment keys that must never be forwarded to external servers
_FORBIDDEN_ENV_KEYS = frozenset({
    "CRUX_HOME", "CRUX_PROJECT", "PYTHONPATH",
    "HOME", "USER", "LOGNAME", "SHELL",
})


@dataclass
class ServerConfig:
    """Configuration for an external MCP server."""
    name: str
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)
    allowed_tools: list[str] | None = None  # None = all tools allowed
    timeout: int = 30
    enabled: bool = True


def _registry_path(crux_dir: str) -> str:
    return os.path.join(crux_dir, "mcp-servers.json")


def _sanitize_env(env: dict[str, str]) -> dict[str, str]:
    """Remove forbidden environment keys to prevent credential leakage."""
    return {k: v for k, v in env.items() if k not in _FORBIDDEN_ENV_KEYS}


def load_registry(crux_dir: str) -> dict[str, ServerConfig]:
    """Load external server registry from .crux/mcp-servers.json."""
    path = _registry_path(crux_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    servers: dict[str, ServerConfig] = {}
    for name, cfg in data.get("servers", {}).items():
        if not isinstance(cfg, dict):
            continue
        servers[name] = ServerConfig(
            name=name,
            command=cfg.get("command", []),
            env=cfg.get("env", {}),
            allowed_tools=cfg.get("allowed_tools"),
            timeout=cfg.get("timeout", 30),
            enabled=cfg.get("enabled", True),
        )
    return servers


def save_registry(crux_dir: str, servers: dict[str, ServerConfig]) -> None:
    """Save server registry to .crux/mcp-servers.json."""
    path = _registry_path(crux_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "servers": {
            name: {
                "command": cfg.command,
                "env": cfg.env,
                "allowed_tools": cfg.allowed_tools,
                "timeout": cfg.timeout,
                "enabled": cfg.enabled,
            }
            for name, cfg in servers.items()
        }
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def register_server(
    crux_dir: str,
    name: str,
    command: list[str],
    env: dict[str, str] | None = None,
    allowed_tools: list[str] | None = None,
    timeout: int = 30,
) -> dict:
    """Register an external MCP server. Overwrites if name exists."""
    servers = load_registry(crux_dir)
    sanitized_env = _sanitize_env(env or {})
    servers[name] = ServerConfig(
        name=name,
        command=command,
        env=sanitized_env,
        allowed_tools=allowed_tools,
        timeout=timeout,
    )
    save_registry(crux_dir, servers)
    return {"registered": True, "name": name}


def remove_server(crux_dir: str, name: str) -> dict:
    """Remove an external MCP server from the registry."""
    servers = load_registry(crux_dir)
    if name not in servers:
        return {"removed": False, "error": f"Server '{name}' not found"}
    del servers[name]
    save_registry(crux_dir, servers)
    return {"removed": True, "name": name}


def list_servers(crux_dir: str) -> dict:
    """List all registered external MCP servers."""
    servers = load_registry(crux_dir)
    return {
        "servers": [
            {
                "name": cfg.name,
                "command": cfg.command,
                "enabled": cfg.enabled,
                "allowed_tools": cfg.allowed_tools,
                "timeout": cfg.timeout,
            }
            for cfg in servers.values()
        ],
        "total": len(servers),
    }
