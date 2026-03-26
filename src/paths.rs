//! Path resolution for .crux/ and ~/.crux/ directories.

use std::env;
use std::path::PathBuf;

/// Get the project's .crux/ directory.
pub fn project_crux_dir() -> PathBuf {
    let project = env::var("CRUX_PROJECT")
        .unwrap_or_else(|_| env::current_dir().unwrap_or_default().to_string_lossy().into());
    PathBuf::from(project).join(".crux")
}

/// Get the user's ~/.crux/ directory.
pub fn user_crux_dir() -> PathBuf {
    let home = env::var("CRUX_HOME")
        .or_else(|_| env::var("HOME"))
        .unwrap_or_default();
    PathBuf::from(home).join(".crux")
}

/// Get the project root directory.
pub fn project_dir() -> PathBuf {
    let project = env::var("CRUX_PROJECT")
        .unwrap_or_else(|_| env::current_dir().unwrap_or_default().to_string_lossy().into());
    PathBuf::from(project)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_crux_dir_ends_with_crux() {
        let dir = project_crux_dir();
        assert!(dir.ends_with(".crux"));
    }

    #[test]
    fn user_crux_dir_ends_with_crux() {
        let dir = user_crux_dir();
        assert!(dir.ends_with(".crux"));
    }
}
