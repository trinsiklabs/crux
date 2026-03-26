//! Gate 1: Pre-flight validation — static checks on scripts.

use regex::Regex;
use super::{ValidationResult, RiskLevel};

/// Validate a script against Crux safety conventions.
pub fn validate(content: &str) -> ValidationResult {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();
    let lines: Vec<&str> = content.lines().collect();

    // Check shebang
    if lines.first().map_or(true, |l| !l.starts_with("#!")) {
        errors.push("Missing shebang (e.g., #!/bin/bash)".into());
    }

    // Check set -euo pipefail
    let has_pipefail = content.contains("set -euo pipefail");
    if !has_pipefail {
        errors.push("Missing 'set -euo pipefail' safety clause".into());
    }

    // Check risk header
    let risk_re = Regex::new(r"(?i)#\s*Risk:\s*(low|medium|high)").unwrap();
    let risk_level = risk_re.captures(content).and_then(|c| RiskLevel::from_str(&c[1]));
    if risk_level.is_none() {
        errors.push("Missing risk header (# Risk: low|medium|high)".into());
    }

    // Check main() function
    if !content.contains("main()") && !content.contains("main ()") {
        warnings.push("No main() function pattern detected".into());
    }

    // Check for banned patterns
    let banned = ["rm -rf /", "sudo rm", ":(){ :|:& };:", "dd if=/dev/zero"];
    for pattern in banned {
        if content.contains(pattern) {
            errors.push(format!("Banned pattern detected: {pattern}"));
        }
    }

    // DRY_RUN support for medium+ risk
    if let Some(risk) = risk_level {
        if matches!(risk, RiskLevel::Medium | RiskLevel::High) && !content.contains("DRY_RUN") {
            warnings.push("Medium/high risk script should support DRY_RUN".into());
        }
    }

    ValidationResult {
        passed: errors.is_empty(),
        errors,
        warnings,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_script_passes() {
        let script = "#!/bin/bash\nset -euo pipefail\n# Risk: low\nmain() {\n  echo hello\n}\nmain\n";
        let result = validate(script);
        assert!(result.passed);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn missing_shebang_fails() {
        let script = "set -euo pipefail\n# Risk: low\n";
        let result = validate(script);
        assert!(!result.passed);
        assert!(result.errors.iter().any(|e| e.contains("shebang")));
    }

    #[test]
    fn missing_pipefail_fails() {
        let script = "#!/bin/bash\n# Risk: low\n";
        let result = validate(script);
        assert!(!result.passed);
        assert!(result.errors.iter().any(|e| e.contains("pipefail")));
    }

    #[test]
    fn banned_pattern_fails() {
        let script = "#!/bin/bash\nset -euo pipefail\n# Risk: low\nrm -rf /\n";
        let result = validate(script);
        assert!(!result.passed);
    }

    #[test]
    fn medium_risk_warns_on_no_dryrun() {
        let script = "#!/bin/bash\nset -euo pipefail\n# Risk: medium\nmain() { echo x; }\n";
        let result = validate(script);
        assert!(result.warnings.iter().any(|w| w.contains("DRY_RUN")));
    }
}
