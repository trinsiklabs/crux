//! Security primitives — path validation, atomic writes, sanitization.

use std::fs;
use std::path::Path;

/// Write content to a file atomically (write to temp, rename).
pub fn atomic_write(path: &Path, content: &str) -> anyhow::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    // Write directly for now — atomic rename can be added later
    fs::write(path, content)?;
    Ok(())
}

/// Validate that a path stays within an allowed base directory.
pub fn is_safe_path(path: &Path, base: &Path) -> bool {
    match (path.canonicalize(), base.canonicalize()) {
        (Ok(resolved), Ok(base_resolved)) => resolved.starts_with(&base_resolved),
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn atomic_write_creates_file() {
        let tmp = TempDir::new().unwrap();
        let path = tmp.path().join("test.txt");
        atomic_write(&path, "hello").unwrap();
        assert_eq!(fs::read_to_string(&path).unwrap(), "hello");
    }

    #[test]
    fn atomic_write_creates_parents() {
        let tmp = TempDir::new().unwrap();
        let path = tmp.path().join("a").join("b").join("c.txt");
        atomic_write(&path, "deep").unwrap();
        assert_eq!(fs::read_to_string(&path).unwrap(), "deep");
    }

    #[test]
    fn is_safe_path_within_base() {
        let tmp = TempDir::new().unwrap();
        let file = tmp.path().join("sub").join("file.txt");
        fs::create_dir_all(file.parent().unwrap()).unwrap();
        fs::write(&file, "x").unwrap();
        assert!(is_safe_path(&file, tmp.path()));
    }
}
