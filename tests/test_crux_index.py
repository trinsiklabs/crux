"""Tests for crux_index — persistent codebase indexing."""

import json
import os
import time

import pytest

from scripts.lib.crux_index import (
    build_catalog,
    detect_language,
    extract_symbols,
    search_index,
    index_stats,
    load_index,
    save_index,
)
from scripts.lib.crux_init import init_project


@pytest.fixture
def repo(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    project = home / "repo"
    project.mkdir()
    init_project(project_dir=str(project))

    (project / "auth.py").write_text(
        "class AuthService:\n    def login(self):\n        pass\n\nAUTH_TIMEOUT = 60\n"
    )
    (project / "db.py").write_text(
        "class Database:\n    def connect(self):\n        pass\n"
    )
    sub = project / "api"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "routes.py").write_text(
        "from auth import AuthService\ndef handle_login():\n    pass\n"
    )
    (project / "readme.md").write_text("# Project\n")
    (project / "config.json").write_text("{}")

    return str(project)


class TestDetectLanguage:
    def test_python(self):
        assert detect_language("auth.py") == "python"

    def test_typescript(self):
        assert detect_language("app.ts") == "typescript"

    def test_elixir(self):
        assert detect_language("lib/app.ex") == "elixir"

    def test_unknown(self):
        assert detect_language("data.xyz") == "unknown"

    def test_javascript(self):
        assert detect_language("index.js") == "javascript"


class TestBuildCatalog:
    def test_returns_dict(self, repo):
        catalog = build_catalog(repo)
        assert isinstance(catalog, dict)

    def test_includes_python_files(self, repo):
        catalog = build_catalog(repo)
        assert "auth.py" in catalog
        assert "db.py" in catalog

    def test_includes_subdirectories(self, repo):
        catalog = build_catalog(repo)
        assert any("routes" in k for k in catalog)

    def test_file_info_fields(self, repo):
        catalog = build_catalog(repo)
        info = catalog["auth.py"]
        assert "language" in info
        assert "lines" in info
        assert "mtime" in info
        assert info["language"] == "python"

    def test_skips_vendored(self, tmp_path):
        r = tmp_path / "r"
        r.mkdir()
        (r / "main.py").write_text("x = 1\n")
        venv = r / ".venv"
        venv.mkdir()
        (venv / "pkg.py").write_text("y = 2\n")
        catalog = build_catalog(str(r))
        assert "main.py" in catalog
        assert not any(".venv" in k for k in catalog)

    def test_nonexistent(self):
        assert build_catalog("/nonexistent") == {}


class TestExtractSymbols:
    def test_python_symbols(self, repo):
        symbols = extract_symbols(os.path.join(repo, "auth.py"), "python")
        names = [s["name"] for s in symbols]
        assert "AuthService" in names
        assert "login" in names

    def test_unknown_language(self, repo):
        symbols = extract_symbols(os.path.join(repo, "config.json"), "unknown")
        assert symbols == []


class TestSearchIndex:
    def test_finds_matching(self, repo):
        results = search_index("auth", repo)
        assert len(results) > 0
        assert any("auth" in r["file"].lower() or "auth" in r.get("symbol", "").lower() for r in results)

    def test_no_match(self, repo):
        results = search_index("zzzznonexistent", repo)
        assert results == []

    def test_empty_query(self, repo):
        assert search_index("", repo) == []

    def test_ranks_exact_higher(self, repo):
        results = search_index("AuthService", repo)
        if len(results) > 1:
            # Exact match should be first
            assert "auth" in results[0]["file"].lower()


class TestIndexPersistence:
    def test_save_and_load(self, repo):
        catalog = build_catalog(repo)
        crux_dir = os.path.join(repo, ".crux")
        save_index(catalog, crux_dir)
        loaded = load_index(crux_dir)
        assert loaded == catalog

    def test_load_nonexistent(self, repo):
        crux_dir = os.path.join(repo, ".crux")
        assert load_index(crux_dir) == {}


class TestExtractSymbolsMultiLang:
    def test_typescript_symbols(self, tmp_path):
        f = tmp_path / "app.ts"
        f.write_text("export function handleLogin() {}\nclass UserService {}\nconst API_URL = 'x'\n")
        symbols = extract_symbols(str(f), "typescript")
        names = [s["name"] for s in symbols]
        assert "handleLogin" in names
        assert "UserService" in names
        assert "API_URL" in names

    def test_javascript_symbols(self, tmp_path):
        f = tmp_path / "app.js"
        f.write_text("function init() {}\nconst config = {}\n")
        symbols = extract_symbols(str(f), "javascript")
        names = [s["name"] for s in symbols]
        assert "init" in names

    def test_elixir_symbols(self, tmp_path):
        f = tmp_path / "app.ex"
        f.write_text("defmodule MyApp do\n  def start do\n  end\nend\n")
        symbols = extract_symbols(str(f), "elixir")
        names = [s["name"] for s in symbols]
        assert "MyApp" in names
        assert "start" in names

    def test_unreadable_file(self, tmp_path):
        from unittest.mock import patch
        f = tmp_path / "bad.ts"
        f.write_text("const x = 1\n")
        with patch("builtins.open", side_effect=OSError):
            symbols = extract_symbols(str(f), "typescript")
        assert symbols == []


class TestCatalogEdge:
    def test_skips_unknown_extension(self, tmp_path):
        r = tmp_path / "r"
        r.mkdir()
        (r / "ok.py").write_text("x = 1\n")
        (r / "data.xyz").write_text("unknown format")
        (r / "binary.dat").write_text("binary data")
        catalog = build_catalog(str(r))
        assert "ok.py" in catalog
        assert "data.xyz" not in catalog
        assert "binary.dat" not in catalog

    def test_os_error_skips_file(self, tmp_path):
        from unittest.mock import patch
        r = tmp_path / "r"
        r.mkdir()
        (r / "ok.py").write_text("x = 1\n")
        (r / "bad.py").write_text("y = 2\n")
        orig_stat = os.stat
        def mock_stat(path, *a, **kw):
            if "bad.py" in str(path):
                raise OSError("no access")
            return orig_stat(path, *a, **kw)
        with patch("os.stat", side_effect=mock_stat):
            catalog = build_catalog(str(r))
        assert "ok.py" in catalog

    def test_includes_ts_files(self, tmp_path):
        r = tmp_path / "r"
        r.mkdir()
        (r / "app.ts").write_text("function main() {}\n")
        catalog = build_catalog(str(r))
        assert "app.ts" in catalog
        assert catalog["app.ts"]["language"] == "typescript"


class TestIndexCorrupt:
    def test_corrupt_json(self, repo):
        crux_dir = os.path.join(repo, ".crux")
        idx_dir = os.path.join(crux_dir, "index")
        os.makedirs(idx_dir, exist_ok=True)
        with open(os.path.join(idx_dir, "catalog.json"), "w") as f:
            f.write("not json{{{")
        loaded = load_index(crux_dir)
        assert loaded == {}


class TestIndexStats:
    def test_returns_stats(self, repo):
        stats = index_stats(repo)
        assert stats["total_files"] > 0
        assert "python" in stats["languages"]
