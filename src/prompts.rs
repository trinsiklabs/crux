//! Prompt quality analysis — bloat detection, improvement suggestions.

use std::fs;
use std::path::Path;

pub struct ModeAudit {
    pub name: String,
    pub word_count: usize,
    pub has_positive_framing: bool,
    pub critical_at_start: bool,
    pub critical_at_end: bool,
    pub issues: Vec<String>,
}

/// Audit a mode prompt for quality.
pub fn audit_mode(path: &Path) -> Option<ModeAudit> {
    let content = fs::read_to_string(path).ok()?;
    let name = path.file_stem()?.to_string_lossy().to_string();

    // Skip frontmatter
    let body = if content.starts_with("---") {
        content.splitn(3, "---").nth(2).unwrap_or(&content)
    } else {
        &content
    };

    let word_count = body.split_whitespace().count();
    let lines: Vec<&str> = body.lines().collect();

    let has_negative = body.contains("don't") || body.contains("never") || body.contains("avoid");
    let has_positive_framing = !has_negative;

    let first_10 = lines.iter().take(10).cloned().collect::<Vec<_>>().join("\n");
    let last_10 = lines.iter().rev().take(10).cloned().collect::<Vec<_>>().join("\n");
    let critical_at_start = first_10.contains("Rule") || first_10.contains("MUST") || first_10.contains("Core");
    let critical_at_end = last_10.contains("Rule") || last_10.contains("MUST") || last_10.contains("Core");

    let mut issues = Vec::new();
    if word_count > 250 {
        issues.push(format!("Prompt too long: {word_count} words (target: 150-200)"));
    }
    if !has_positive_framing {
        issues.push("Contains negative framing (don't/never/avoid)".into());
    }
    if !critical_at_start {
        issues.push("No critical rules at start (prime position)".into());
    }
    if !critical_at_end {
        issues.push("No critical rules at end (prime position)".into());
    }

    Some(ModeAudit {
        name,
        word_count,
        has_positive_framing,
        critical_at_start,
        critical_at_end,
        issues,
    })
}

/// Audit all modes in a directory.
pub fn audit_all_modes(modes_dir: &Path) -> Vec<ModeAudit> {
    let mut results = Vec::new();
    if let Ok(entries) = fs::read_dir(modes_dir) {
        for entry in entries.flatten() {
            if entry.path().extension().map_or(false, |e| e == "md") {
                if let Some(audit) = audit_mode(&entry.path()) {
                    results.push(audit);
                }
            }
        }
    }
    results.sort_by_key(|a| a.name.clone());
    results
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn audit_good_mode() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("test.md");
        fs::write(&f, "---\ntemperature: 0.6\n---\n\n## Core Rules\nAlways validate inputs.\n\n## Core Rules (end)\nAlways check types.").unwrap();
        let audit = audit_mode(&f).unwrap();
        assert_eq!(audit.name, "test");
        assert!(audit.word_count < 250);
    }

    #[test]
    fn audit_detects_bloat() {
        let tmp = TempDir::new().unwrap();
        let f = tmp.path().join("bloated.md");
        let words = "word ".repeat(300);
        fs::write(&f, &words).unwrap();
        let audit = audit_mode(&f).unwrap();
        assert!(audit.issues.iter().any(|i| i.contains("too long")));
    }
}
