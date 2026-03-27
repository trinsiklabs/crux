//! Ollama REST API client — local LLM for adversarial auditing.

use serde::{Deserialize, Serialize};

const DEFAULT_ENDPOINT: &str = "http://localhost:11434";

#[derive(Debug, Serialize)]
struct GenerateRequest {
    model: String,
    prompt: String,
    stream: bool,
}

#[derive(Debug, Deserialize)]
struct GenerateResponse {
    response: String,
}

#[derive(Debug, Deserialize)]
struct TagsResponse {
    models: Vec<ModelInfo>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ModelInfo {
    pub name: String,
    pub size: Option<u64>,
}

/// Check if Ollama is running.
pub fn check_running(endpoint: Option<&str>) -> bool {
    let url = format!("{}/api/tags", endpoint.unwrap_or(DEFAULT_ENDPOINT));
    reqwest::blocking::get(&url).is_ok()
}

/// List available models.
pub fn list_models(endpoint: Option<&str>) -> Vec<ModelInfo> {
    let url = format!("{}/api/tags", endpoint.unwrap_or(DEFAULT_ENDPOINT));
    match reqwest::blocking::get(&url) {
        Ok(resp) => resp.json::<TagsResponse>()
            .map(|t| t.models)
            .unwrap_or_default(),
        Err(_) => Vec::new(),
    }
}

/// Generate text from a model.
pub fn generate(model: &str, prompt: &str, endpoint: Option<&str>) -> Result<String, String> {
    let url = format!("{}/api/generate", endpoint.unwrap_or(DEFAULT_ENDPOINT));
    let req = GenerateRequest {
        model: model.into(),
        prompt: prompt.into(),
        stream: false,
    };

    let client = reqwest::blocking::Client::new();
    match client.post(&url).json(&req).send() {
        Ok(resp) => {
            if resp.status().is_success() {
                resp.json::<GenerateResponse>()
                    .map(|r| r.response)
                    .map_err(|e| e.to_string())
            } else {
                Err(format!("Ollama error: {}", resp.status()))
            }
        }
        Err(e) => Err(format!("Connection failed: {e}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn check_running_handles_failure() {
        // Should return false when Ollama isn't running on this port
        assert!(!check_running(Some("http://localhost:99999")));
    }

    #[test]
    fn list_models_handles_failure() {
        assert!(list_models(Some("http://localhost:99999")).is_empty());
    }
}
