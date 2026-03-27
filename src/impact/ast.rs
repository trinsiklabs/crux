//! AST-based file analysis — multi-language via tree-sitter.
//!
//! Extracts imports, definitions, and builds import graphs for
//! Python, JavaScript, TypeScript, and Rust files.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use tree_sitter::{Language, Parser};

const SKIP_DIRS: &[&str] = &[
    "node_modules", ".git", ".venv", "__pycache__", "vendor",
    "dist", "build", "_site", "target",
];

/// A symbol definition extracted from source code.
#[derive(Debug, Clone)]
pub struct Definition {
    pub name: String,
    pub kind: String, // "function", "class", "constant", "method"
    pub line: usize,
}

fn get_parser(ext: &str) -> Option<Parser> {
    let language = match ext {
        "py" => tree_sitter_python::LANGUAGE,
        "js" | "jsx" => tree_sitter_javascript::LANGUAGE,
        "ts" | "tsx" => tree_sitter_typescript::LANGUAGE_TYPESCRIPT,
        "rs" => tree_sitter_rust::LANGUAGE,
        _ => return None,
    };
    let mut parser = Parser::new();
    parser.set_language(&language.into()).ok()?;
    Some(parser)
}

/// Parse imports from a source file.
pub fn parse_imports(path: &Path) -> Vec<String> {
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
    let mut parser = match get_parser(ext) {
        Some(p) => p,
        None => return Vec::new(),
    };

    let source = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(_) => return Vec::new(),
    };

    let tree = match parser.parse(&source, None) {
        Some(t) => t,
        None => return Vec::new(),
    };

    let mut imports = Vec::new();
    let mut cursor = tree.walk();

    // Walk top-level nodes
    if cursor.goto_first_child() {
        loop {
            let node = cursor.node();
            let kind = node.kind();

            match ext {
                "py" => {
                    if kind == "import_statement" || kind == "import_from_statement" {
                        // Extract module name from the import
                        if let Some(name_node) = node.child_by_field_name("module_name")
                            .or_else(|| node.child_by_field_name("name"))
                        {
                            let name = &source[name_node.byte_range()];
                            let root = name.split('.').next().unwrap_or(name);
                            imports.push(root.to_string());
                        }
                    }
                }
                "js" | "jsx" | "ts" | "tsx" => {
                    if kind == "import_statement" {
                        // Extract from string in import
                        let text = &source[node.byte_range()];
                        if let Some(start) = text.find('\'').or_else(|| text.find('"')) {
                            if let Some(end) = text[start+1..].find('\'').or_else(|| text[start+1..].find('"')) {
                                let module = &text[start+1..start+1+end];
                                let root = module.split('/').next().unwrap_or(module);
                                imports.push(root.to_string());
                            }
                        }
                    }
                }
                "rs" => {
                    if kind == "use_declaration" {
                        let text = &source[node.byte_range()];
                        // Extract crate name from "use crate_name::..."
                        let trimmed = text.trim_start_matches("use ").trim_end_matches(';');
                        let root = trimmed.split("::").next().unwrap_or(trimmed);
                        imports.push(root.to_string());
                    }
                }
                _ => {}
            }

            if !cursor.goto_next_sibling() {
                break;
            }
        }
    }

    imports
}

/// Parse function/class/constant definitions from a source file.
pub fn parse_definitions(path: &Path) -> Vec<Definition> {
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
    let mut parser = match get_parser(ext) {
        Some(p) => p,
        None => return Vec::new(),
    };

    let source = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(_) => return Vec::new(),
    };

    let tree = match parser.parse(&source, None) {
        Some(t) => t,
        None => return Vec::new(),
    };

    let mut defs = Vec::new();
    collect_definitions(&tree.root_node(), &source, ext, &mut defs);
    defs
}

fn collect_definitions(node: &tree_sitter::Node, source: &str, ext: &str, defs: &mut Vec<Definition>) {
    let kind = node.kind();
    let line = node.start_position().row + 1;

    match ext {
        "py" => {
            if kind == "function_definition" || kind == "class_definition" {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = source[name_node.byte_range()].to_string();
                    let def_kind = if kind == "class_definition" { "class" } else { "function" };
                    defs.push(Definition { name, kind: def_kind.into(), line });
                }
            }
            if kind == "assignment" {
                // Check for UPPER_CASE constants
                if let Some(left) = node.child_by_field_name("left") {
                    let name = &source[left.byte_range()];
                    if name.chars().all(|c| c.is_uppercase() || c == '_') && name.len() > 1 {
                        defs.push(Definition { name: name.to_string(), kind: "constant".into(), line });
                    }
                }
            }
        }
        "js" | "jsx" | "ts" | "tsx" => {
            if kind == "function_declaration" || kind == "class_declaration" {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = source[name_node.byte_range()].to_string();
                    let def_kind = if kind == "class_declaration" { "class" } else { "function" };
                    defs.push(Definition { name, kind: def_kind.into(), line });
                }
            }
            if kind == "lexical_declaration" || kind == "variable_declaration" {
                // const X = ..., let X = ...
                for i in 0..node.child_count() {
                    if let Some(child) = node.child(i) {
                        if child.kind() == "variable_declarator" {
                            if let Some(name_node) = child.child_by_field_name("name") {
                                let name = source[name_node.byte_range()].to_string();
                                defs.push(Definition { name, kind: "constant".into(), line });
                            }
                        }
                    }
                }
            }
            if kind == "export_statement" {
                // Export default/named — recurse into child
                for i in 0..node.child_count() {
                    if let Some(child) = node.child(i) {
                        collect_definitions(&child, source, ext, defs);
                    }
                }
                return; // Don't recurse again below
            }
        }
        "rs" => {
            if kind == "function_item" {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = source[name_node.byte_range()].to_string();
                    defs.push(Definition { name, kind: "function".into(), line });
                }
            }
            if kind == "struct_item" || kind == "enum_item" || kind == "impl_item" {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = source[name_node.byte_range()].to_string();
                    defs.push(Definition { name, kind: kind.trim_end_matches("_item").into(), line });
                }
            }
            if kind == "const_item" || kind == "static_item" {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = source[name_node.byte_range()].to_string();
                    defs.push(Definition { name, kind: "constant".into(), line });
                }
            }
        }
        _ => {}
    }

    // Recurse into children
    for i in 0..node.child_count() {
        if let Some(child) = node.child(i) {
            collect_definitions(&child, source, ext, defs);
        }
    }
}

/// Build import graph for all source files in a directory.
pub fn build_import_graph(root: &Path) -> HashMap<String, Vec<String>> {
    if !root.is_dir() {
        return HashMap::new();
    }

    let mut graph: HashMap<String, Vec<String>> = HashMap::new();

    for entry in walkdir::WalkDir::new(root)
        .into_iter()
        .filter_entry(|e| {
            let name = e.file_name().to_string_lossy();
            !SKIP_DIRS.contains(&name.as_ref())
        })
        .filter_map(|e| e.ok())
    {
        let path = entry.path();
        if !path.is_file() {
            continue;
        }
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
        if !["py", "js", "jsx", "ts", "tsx", "rs"].contains(&ext) {
            continue;
        }

        let imports = parse_imports(path);
        if !imports.is_empty() {
            let rel = path.strip_prefix(root).unwrap_or(path).to_string_lossy().to_string();
            graph.insert(rel, imports);
        }
    }

    graph
}

/// Score files by how many of their definitions match keywords.
/// Includes hub boost for files imported by many others.
pub fn symbol_relevance(root: &Path, keywords: &[String]) -> HashMap<String, f64> {
    if keywords.is_empty() || !root.is_dir() {
        return HashMap::new();
    }

    let lower_keywords: HashSet<String> = keywords.iter().map(|k| k.to_lowercase()).collect();
    let mut scores: HashMap<String, f64> = HashMap::new();

    // Build import graph for hub scoring
    let graph = build_import_graph(root);
    let mut import_counts: HashMap<String, u32> = HashMap::new();
    for imports in graph.values() {
        for imp in imports {
            *import_counts.entry(imp.clone()).or_insert(0) += 1;
        }
    }

    for entry in walkdir::WalkDir::new(root)
        .into_iter()
        .filter_entry(|e| !SKIP_DIRS.contains(&e.file_name().to_string_lossy().as_ref()))
        .filter_map(|e| e.ok())
    {
        let path = entry.path();
        if !path.is_file() {
            continue;
        }
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
        if !["py", "js", "jsx", "ts", "tsx", "rs"].contains(&ext) {
            continue;
        }

        let rel = path.strip_prefix(root).unwrap_or(path).to_string_lossy().to_string();
        let defs = parse_definitions(path);

        for def in &defs {
            let name_lower = def.name.to_lowercase();
            for kw in &lower_keywords {
                if kw.contains(&name_lower) || name_lower.contains(kw.as_str()) {
                    *scores.entry(rel.clone()).or_insert(0.0) += 2.0;
                }
            }
        }

        // Hub boost
        let module_name = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
        let hub_count = import_counts.get(&module_name).copied().unwrap_or(0);
        if hub_count > 0 && scores.contains_key(&rel) {
            *scores.entry(rel).or_insert(0.0) += hub_count as f64 * 0.5;
        }
    }

    // Normalize
    if scores.is_empty() {
        return HashMap::new();
    }
    let mx = scores.values().cloned().fold(0.0_f64, f64::max).max(1.0);
    scores.iter().map(|(k, v)| (k.clone(), (v / mx * 1000000.0).round() / 1000000.0)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn parse_python_imports() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("test.py");
        fs::write(&f, "import os\nfrom pathlib import Path\nfrom .utils import helper\n").unwrap();
        let imports = parse_imports(&f);
        assert!(imports.contains(&"os".to_string()));
    }

    #[test]
    fn parse_python_definitions() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("test.py");
        fs::write(&f, "class AuthService:\n    def login(self):\n        pass\n\nMAX_RETRY = 3\n").unwrap();
        let defs = parse_definitions(&f);
        let names: Vec<&str> = defs.iter().map(|d| d.name.as_str()).collect();
        assert!(names.contains(&"AuthService"));
        assert!(names.contains(&"login"));
        assert!(names.contains(&"MAX_RETRY"));
    }

    #[test]
    fn parse_rust_definitions() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("test.rs");
        fs::write(&f, "pub fn handle_request() {}\npub struct Server {}\nconst MAX: u32 = 10;\n").unwrap();
        let defs = parse_definitions(&f);
        let names: Vec<&str> = defs.iter().map(|d| d.name.as_str()).collect();
        assert!(names.contains(&"handle_request"));
        assert!(names.contains(&"Server"));
        assert!(names.contains(&"MAX"));
    }

    #[test]
    fn parse_js_definitions() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("test.js");
        fs::write(&f, "function init() {}\nclass App {}\nconst CONFIG = {};\n").unwrap();
        let defs = parse_definitions(&f);
        let names: Vec<&str> = defs.iter().map(|d| d.name.as_str()).collect();
        assert!(names.contains(&"init"));
        assert!(names.contains(&"App"));
    }

    #[test]
    fn symbol_relevance_scores_matching() {
        let tmp = TempDir::new().unwrap();
        let dir = tmp.path();
        fs::write(dir.join("auth.py"), "class AuthService:\n    def login(self):\n        pass\n").unwrap();
        fs::write(dir.join("db.py"), "class Database:\n    pass\n").unwrap();
        let scores = symbol_relevance(dir, &["auth".into(), "login".into()]);
        assert!(scores.contains_key("auth.py"));
        assert!(*scores.get("auth.py").unwrap_or(&0.0) > 0.0);
    }

    #[test]
    fn empty_keywords() {
        let tmp = TempDir::new().unwrap();
        assert!(symbol_relevance(tmp.path(), &[]).is_empty());
    }

    #[test]
    fn nonexistent_dir() {
        assert!(symbol_relevance(Path::new("/nonexistent"), &["x".into()]).is_empty());
    }

    #[test]
    fn unsupported_extension() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("test.xyz");
        fs::write(&f, "whatever").unwrap();
        assert!(parse_imports(&f).is_empty());
        assert!(parse_definitions(&f).is_empty());
    }
}
