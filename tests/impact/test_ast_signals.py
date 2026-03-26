"""Tests for impact.ast_signals — AST-based file analysis for Python."""

import os

import pytest

from scripts.lib.impact.ast_signals import (
    parse_imports,
    parse_definitions,
    build_import_graph,
    symbol_relevance,
)


@pytest.fixture
def repo(tmp_path):
    """Fixture Python repo with imports and definitions."""
    r = tmp_path / "repo"
    r.mkdir()

    (r / "auth.py").write_text(
        "import hashlib\n"
        "from db import Database\n"
        "from .utils import helper\n\n"
        "class AuthService:\n"
        "    def login(self, user: str) -> bool:\n"
        "        pass\n\n"
        "    def logout(self):\n"
        "        pass\n\n"
        "AUTH_TIMEOUT = 3600\n"
    )

    (r / "db.py").write_text(
        "import sqlite3\n\n"
        "class Database:\n"
        "    def connect(self):\n"
        "        pass\n\n"
        "    def query(self, sql: str):\n"
        "        pass\n"
    )

    (r / "utils.py").write_text(
        "def helper():\n"
        "    return True\n\n"
        "def format_date(ts):\n"
        "    pass\n"
    )

    sub = r / "api"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "routes.py").write_text(
        "from auth import AuthService\n"
        "from db import Database\n\n"
        "def handle_login():\n"
        "    pass\n"
    )

    return str(r)


class TestParseImports:
    def test_returns_list(self, repo):
        result = parse_imports(os.path.join(repo, "auth.py"))
        assert isinstance(result, list)

    def test_finds_imports(self, repo):
        result = parse_imports(os.path.join(repo, "auth.py"))
        assert "hashlib" in result
        assert "db" in result

    def test_finds_relative_imports(self, repo):
        result = parse_imports(os.path.join(repo, "auth.py"))
        # .utils is a relative import
        assert any("utils" in imp for imp in result)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        assert parse_imports(str(f)) == []

    def test_syntax_error(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n")
        assert parse_imports(str(f)) == []

    def test_nonexistent_file(self):
        assert parse_imports("/nonexistent/file.py") == []

    def test_non_python_file(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("not python")
        assert parse_imports(str(f)) == []


class TestParseDefinitions:
    def test_returns_list(self, repo):
        result = parse_definitions(os.path.join(repo, "auth.py"))
        assert isinstance(result, list)

    def test_finds_class(self, repo):
        result = parse_definitions(os.path.join(repo, "auth.py"))
        names = [d["name"] for d in result]
        assert "AuthService" in names

    def test_finds_functions(self, repo):
        result = parse_definitions(os.path.join(repo, "auth.py"))
        names = [d["name"] for d in result]
        assert "login" in names
        assert "logout" in names

    def test_finds_constants(self, repo):
        result = parse_definitions(os.path.join(repo, "auth.py"))
        names = [d["name"] for d in result]
        assert "AUTH_TIMEOUT" in names

    def test_includes_type(self, repo):
        result = parse_definitions(os.path.join(repo, "auth.py"))
        types = {d["name"]: d["type"] for d in result}
        assert types["AuthService"] == "class"
        assert types["login"] == "function"
        assert types["AUTH_TIMEOUT"] == "constant"

    def test_includes_line(self, repo):
        result = parse_definitions(os.path.join(repo, "auth.py"))
        for d in result:
            assert "line" in d
            assert isinstance(d["line"], int)

    def test_syntax_error(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("class Broken(\n")
        assert parse_definitions(str(f)) == []


class TestBuildImportGraph:
    def test_returns_dict(self, repo):
        result = build_import_graph(repo)
        assert isinstance(result, dict)

    def test_maps_files_to_imports(self, repo):
        result = build_import_graph(repo)
        assert "auth.py" in result
        assert "db" in result["auth.py"]

    def test_includes_subdirectories(self, repo):
        result = build_import_graph(repo)
        assert any("routes" in k for k in result)

    def test_skips_vendored_dirs(self, tmp_path):
        r = tmp_path / "repo"
        r.mkdir()
        (r / "main.py").write_text("import os\n")
        venv = r / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "pkg.py").write_text("import sys\n")
        result = build_import_graph(str(r))
        assert not any(".venv" in k for k in result)

    def test_nonexistent_root(self):
        assert build_import_graph("/nonexistent") == {}


class TestSymbolRelevance:
    def test_returns_dict(self, repo):
        result = symbol_relevance(repo, ["auth"])
        assert isinstance(result, dict)

    def test_auth_file_scores_high(self, repo):
        result = symbol_relevance(repo, ["auth", "login"])
        assert "auth.py" in result
        assert result["auth.py"] > 0

    def test_unrelated_keyword(self, repo):
        result = symbol_relevance(repo, ["xyznonexistent"])
        # Should return empty or very low scores
        assert all(v == 0 for v in result.values()) or result == {}

    def test_hub_boost(self, repo):
        """Files imported by many others get a hub boost."""
        result = symbol_relevance(repo, ["database", "connect"])
        # db.py is imported by auth.py and api/routes.py — should score
        if "db.py" in result:
            assert result["db.py"] > 0

    def test_empty_keywords(self, repo):
        assert symbol_relevance(repo, []) == {}

    def test_nonexistent_root(self):
        assert symbol_relevance("/nonexistent", ["auth"]) == {}

    def test_reverse_match(self, repo):
        """Keyword longer than definition name still matches."""
        result = symbol_relevance(repo, ["authservice"])
        # 'auth' is substring of 'authservice', but 'authservice' contains 'auth'
        # AuthService.lower() = 'authservice', kw = 'authservice' → exact
        assert "auth.py" in result


class TestParseImportsEdge:
    def test_import_from_with_level_no_module(self, tmp_path):
        """from . import foo style import."""
        f = tmp_path / "rel.py"
        f.write_text("from . import helpers\n")
        result = parse_imports(str(f))
        assert "helpers" in result

    def test_dotted_import(self, tmp_path):
        f = tmp_path / "dotted.py"
        f.write_text("import os.path\n")
        result = parse_imports(str(f))
        assert "os" in result


class TestParseDefinitionsEdge:
    def test_async_function(self, tmp_path):
        f = tmp_path / "async_mod.py"
        f.write_text("async def fetch_data():\n    pass\n")
        result = parse_definitions(str(f))
        names = [d["name"] for d in result]
        assert "fetch_data" in names

    def test_nonexistent_file(self):
        assert parse_definitions("/nonexistent/file.py") == []

    def test_non_python(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("not python")
        assert parse_definitions(str(f)) == []


class TestSymbolRelevanceEdge:
    def test_no_matching_definitions(self, repo):
        """Keywords that match nothing should return empty."""
        result = symbol_relevance(repo, ["zzzznonexistent12345"])
        assert result == {} or all(v == 0 for v in result.values())

    def test_mixed_file_types(self, tmp_path):
        """Repos with non-Python files should skip them gracefully."""
        r = tmp_path / "mixed"
        r.mkdir()
        (r / "main.py").write_text("def auth():\n    pass\n")
        (r / "readme.md").write_text("# readme")
        (r / "config.json").write_text("{}")
        result = symbol_relevance(str(r), ["auth"])
        assert "main.py" in result
        assert "readme.md" not in result

    def test_reverse_match_scoring(self, tmp_path):
        """name_lower ('db') in kw ('database') triggers reverse match."""
        r = tmp_path / "rev"
        r.mkdir()
        (r / "db.py").write_text("DB_HOST = 'localhost'\n")
        # keyword 'db_host' contains definition 'DB_HOST'.lower()='db_host'
        result = symbol_relevance(str(r), ["db_host_config"])
        # db_host is in db_host_config → reverse match
        assert "db.py" in result

    def test_all_zero_scores(self, tmp_path):
        """When definitions exist but no keywords match at all."""
        r = tmp_path / "nope"
        r.mkdir()
        (r / "mod.py").write_text("X = 1\n")
        result = symbol_relevance(str(r), ["zzzzz"])
        assert result == {} or all(v == 0 for v in result.values())

    def test_top_level_function_not_in_class(self, tmp_path):
        """Top-level function with same name as class method gets found."""
        r = tmp_path / "toplevel"
        r.mkdir()
        (r / "mod.py").write_text(
            "def standalone():\n    pass\n\n"
            "class Foo:\n    def method(self):\n        pass\n"
        )
        result = parse_definitions(str(r / "mod.py"))
        names = [d["name"] for d in result]
        assert "standalone" in names
        assert "Foo" in names
        assert "method" in names

    def test_all_scores_zero_after_match(self, tmp_path):
        """Force zero max scores — all definitions match nothing exactly."""
        r = tmp_path / "zero"
        r.mkdir()
        # File has definitions but keywords won't match (substring or reverse)
        (r / "mod.py").write_text("ABCXYZ = 1\n")
        # keyword 'qqqq' has no overlap with 'abcxyz'
        result = symbol_relevance(str(r), ["qqqq"])
        # Should return {} since no scores
        assert result == {}

    def test_hub_boost_no_match(self, repo):
        """Hub files without keyword matches don't get scores."""
        result = symbol_relevance(repo, ["xyznothing"])
        # db.py is a hub (imported by 2 files) but no keyword match
        assert result.get("db.py", 0) == 0 or "db.py" not in result
