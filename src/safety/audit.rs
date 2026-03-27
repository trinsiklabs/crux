//! Gate 3: Recursive security audit — scan for vulnerabilities.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::sync::LazyLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditState {
    pub iteration: u32,
    pub max_iterations: u32,
    pub findings: Vec<Finding>,
    pub converged: bool,
    pub started: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub category: String,
    pub severity: String,
    pub description: String,
    pub file: String,
    pub line: Option<usize>,
    pub cwe: Option<String>,
}

static VULNERABILITY_PATTERNS: LazyLock<Vec<(&str, &str, &str, Regex)>> = LazyLock::new(|| {
    vec![
        ("injection", "high", "CWE-78", Regex::new(r"(?i)(os\.system|subprocess\.call|exec\(|eval\()").unwrap()),
        ("path_traversal", "high", "CWE-22", Regex::new(r"(?i)(\.\./|\.\.\\|path\.join.*user)").unwrap()),
        ("hardcoded_secret", "high", "CWE-798", Regex::new(r#"(?i)(password\s*=\s*["'][^"']+["']|api_key\s*=\s*["'])"#).unwrap()),
        ("sql_injection", "high", "CWE-89", Regex::new(r#"(?i)(f["'].*SELECT|\.format\(.*SELECT|%s.*SELECT)"#).unwrap()),
        ("insecure_http", "medium", "CWE-319", Regex::new(r"http://(?!localhost|127\.0\.0\.1)").unwrap()),
        ("debug_enabled", "medium", "CWE-489", Regex::new(r"(?i)(debug\s*=\s*true|DEBUG\s*=\s*True)").unwrap()),
        ("weak_crypto", "medium", "CWE-327", Regex::new(r"(?i)(md5|sha1)\(").unwrap()),
    ]
});

impl Default for AuditState {
    fn default() -> Self {
        Self {
            iteration: 0,
            max_iterations: 3,
            findings: Vec::new(),
            converged: false,
            started: chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
        }
    }
}

pub fn start(crux_dir: &Path) -> AuditState {
    let state = AuditState::default();
    save_state(crux_dir, &state);
    state
}

pub fn scan_file(path: &Path) -> Vec<Finding> {
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(_) => return Vec::new(),
    };
    let file_str = path.to_string_lossy().to_string();
    let mut findings = Vec::new();

    for (category, severity, cwe, pattern) in VULNERABILITY_PATTERNS.iter() {
        for (line_num, line) in content.lines().enumerate() {
            if pattern.is_match(line) {
                findings.push(Finding {
                    category: category.to_string(),
                    severity: severity.to_string(),
                    description: format!("Potential {category} vulnerability"),
                    file: file_str.clone(),
                    line: Some(line_num + 1),
                    cwe: Some(cwe.to_string()),
                });
            }
        }
    }

    findings
}

pub fn summary(crux_dir: &Path) -> AuditState {
    let path = crux_dir.join("security_audit/state.json");
    match fs::read_to_string(&path) {
        Ok(content) => serde_json::from_str(&content).unwrap_or_default(),
        Err(_) => AuditState { converged: false, ..Default::default() },
    }
}

fn save_state(crux_dir: &Path, state: &AuditState) {
    let path = crux_dir.join("security_audit/state.json");
    let _ = fs::create_dir_all(path.parent().unwrap());
    let _ = fs::write(&path, serde_json::to_string_pretty(state).unwrap_or_default());
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn start_creates_state() {
        let tmp = TempDir::new().unwrap();
        let crux = tmp.path().join(".crux");
        fs::create_dir_all(&crux).unwrap();
        let state = start(&crux);
        assert_eq!(state.iteration, 0);
        assert_eq!(state.max_iterations, 3);
    }

    #[test]
    fn scan_detects_injection() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("bad.py");
        fs::write(&f, "import os\nos.system(user_input)\n").unwrap();
        let findings = scan_file(&f);
        assert!(!findings.is_empty());
        assert!(findings.iter().any(|f| f.category == "injection"));
    }

    #[test]
    fn scan_detects_hardcoded_secret() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("config.py");
        fs::write(&f, "password = 'hunter2'\n").unwrap();
        let findings = scan_file(&f);
        assert!(findings.iter().any(|f| f.category == "hardcoded_secret"));
    }

    #[test]
    fn scan_clean_file() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("clean.py");
        fs::write(&f, "def hello():\n    return 'world'\n").unwrap();
        let findings = scan_file(&f);
        assert!(findings.is_empty());
    }
}
