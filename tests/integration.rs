//! Integration tests for the Rust MCP server — end-to-end via JSON-RPC.
//!
//! Spawns the crux binary as a subprocess and communicates via MCP protocol.
//! Tests that all 56 tools are registered and callable.

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};
use std::time::Duration;

/// Helper: spawn the crux MCP server and send/receive JSON-RPC messages.
struct McpClient {
    child: std::process::Child,
    stdin: std::process::ChildStdin,
    reader: BufReader<std::process::ChildStdout>,
}

impl McpClient {
    fn new() -> Self {
        let mut child = Command::new(env!("CARGO_BIN_EXE_crux"))
            .args(["mcp", "start"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .expect("Failed to start crux mcp");

        let stdin = child.stdin.take().unwrap();
        let stdout = child.stdout.take().unwrap();
        let reader = BufReader::new(stdout);

        let mut client = Self { child, stdin, reader };

        // Initialize
        let init_resp = client.call(json!({
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1"}
            }
        }));
        assert_eq!(init_resp["result"]["protocolVersion"], "2024-11-05");

        // Send initialized notification
        client.send(json!({
            "jsonrpc": "2.0", "method": "notifications/initialized"
        }));

        client
    }

    fn send(&mut self, msg: Value) {
        let s = serde_json::to_string(&msg).unwrap();
        writeln!(self.stdin, "{}", s).unwrap();
        self.stdin.flush().unwrap();
    }

    fn recv(&mut self) -> Value {
        let mut line = String::new();
        self.reader.read_line(&mut line).unwrap();
        serde_json::from_str(line.trim()).unwrap()
    }

    fn call(&mut self, msg: Value) -> Value {
        let id = msg.get("id").cloned();
        self.send(msg);
        // Read lines until we get a response with matching id (or timeout)
        let deadline = std::time::Instant::now() + Duration::from_secs(5);
        loop {
            if std::time::Instant::now() > deadline {
                panic!("Timeout waiting for response");
            }
            let mut line = String::new();
            self.reader.read_line(&mut line).unwrap();
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            if let Ok(resp) = serde_json::from_str::<Value>(trimmed) {
                // If it's a notification (no id), skip it
                if resp.get("id").is_none() && resp.get("method").is_some() {
                    continue;
                }
                // If we sent a specific id, match it
                if let Some(ref expected_id) = id {
                    if resp.get("id") == Some(expected_id) {
                        return resp;
                    }
                }
                return resp;
            }
        }
    }

    fn list_tools(&mut self) -> Vec<Value> {
        let resp = self.call(json!({
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
        }));
        resp["result"]["tools"].as_array().unwrap().clone()
    }

    fn call_tool(&mut self, name: &str, args: Value, id: u64) -> Value {
        // Build params — omit arguments entirely for parameterless tools
        let params = if args.is_null() || (args.is_object() && args.as_object().unwrap().is_empty()) {
            json!({"name": name})
        } else {
            json!({"name": name, "arguments": args})
        };
        let resp = self.call(json!({
            "jsonrpc": "2.0", "id": id, "method": "tools/call",
            "params": params
        }));
        // Parse the text content from the tool result
        let content = &resp["result"]["content"];
        if let Some(arr) = content.as_array() {
            if let Some(first) = arr.first() {
                if let Some(text) = first["text"].as_str() {
                    return serde_json::from_str(text).unwrap_or(json!({"raw": text}));
                }
            }
        }
        resp
    }
}

impl Drop for McpClient {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

// ==========================================================================
// Layer 1: Tool Registration
// ==========================================================================

#[test]
fn all_56_tools_registered() {
    let mut client = McpClient::new();
    let tools = client.list_tools();
    assert_eq!(tools.len(), 56, "Expected 56 tools, got {}", tools.len());
}

#[test]
fn expected_tool_names_present() {
    let mut client = McpClient::new();
    let tools = client.list_tools();
    let names: Vec<&str> = tools.iter().filter_map(|t| t["name"].as_str()).collect();

    let expected = vec![
        "get_session_state", "update_session", "restore_context",
        "write_handoff", "read_handoff", "lookup_knowledge",
        "promote_knowledge", "remember_fact", "recall_memories",
        "forget_fact", "list_all_memories", "analyze_impact",
        "search_code", "index_codebase", "validate_script",
        "get_active_gates", "get_pipeline_config",
        "git_context", "git_diff", "git_risky_files", "git_suggest_commit",
        "log_correction", "log_interaction",
        "get_mode_prompt", "list_modes",
        "switch_tool_to", "verify_health",
        "register_mcp_server", "list_mcp_servers", "remove_mcp_server",
        "bip_generate", "bip_approve", "bip_status", "bip_get_analytics",
        "get_model_for_task", "get_available_tiers", "get_mode_model", "get_model_quality_stats",
        "start_tdd_gate", "check_tdd_status",
        "start_security_audit", "security_audit_summary",
        "start_design_validation", "design_validation_summary", "check_contrast",
        "figma_get_tokens", "figma_get_components",
        "register_project", "get_cross_project_digest",
        "check_processor_thresholds", "run_background_processors", "get_processor_status",
        "audit_script_8b", "audit_script_32b",
        "get_project_context", "get_digest",
    ];

    for name in &expected {
        assert!(names.contains(name), "Missing tool: {name}");
    }
}

#[test]
fn all_tools_have_descriptions() {
    let mut client = McpClient::new();
    let tools = client.list_tools();
    for tool in &tools {
        let name = tool["name"].as_str().unwrap();
        let desc = tool["description"].as_str().unwrap_or("");
        assert!(!desc.is_empty(), "Tool {name} has no description");
    }
}

#[test]
fn all_tools_have_input_schema() {
    let mut client = McpClient::new();
    let tools = client.list_tools();
    for tool in &tools {
        let name = tool["name"].as_str().unwrap();
        let schema = &tool["inputSchema"];
        // Parameterless tools have {"const": null}, others have {"type": "object"}
        assert!(
            schema.get("type").is_some() || schema.get("const").is_some(),
            "Tool {name} has no valid schema: {schema}"
        );
    }
}

// ==========================================================================
// Layer 2: Session Tools (via MCP protocol)
// ==========================================================================

#[test]
fn get_session_state_returns_json() {
    let mut client = McpClient::new();
    let result = client.call_tool("get_session_state", json!({}), 10);
    assert!(result.get("active_mode").is_some(), "Missing active_mode: {result}");
}

#[test]
fn update_session_modifies_state() {
    let mut client = McpClient::new();
    client.call_tool("update_session", json!({"working_on": "test task"}), 10);
    let state = client.call_tool("get_session_state", json!({}), 11);
    assert_eq!(state["working_on"], "test task");
}

#[test]
fn write_read_handoff_roundtrip() {
    let mut client = McpClient::new();
    client.call_tool("write_handoff", json!({"content": "test handoff"}), 10);
    let result = client.call_tool("read_handoff", json!({}), 11);
    assert_eq!(result["exists"], true);
    assert!(result["content"].as_str().unwrap().contains("test handoff"));
}

// ==========================================================================
// Layer 2: Safety Tools
// ==========================================================================

#[test]
fn validate_script_passes_good() {
    let mut client = McpClient::new();
    let result = client.call_tool("validate_script", json!({
        "content": "#!/bin/bash\nset -euo pipefail\n# Risk: low\nmain() {\n  echo hi\n}\nmain"
    }), 10);
    assert_eq!(result["passed"], true);
}

#[test]
fn validate_script_fails_bad() {
    let mut client = McpClient::new();
    let result = client.call_tool("validate_script", json!({"content": "echo hi"}), 10);
    assert_eq!(result["passed"], false);
}

#[test]
fn active_gates_scale_with_risk() {
    let mut client = McpClient::new();
    let low = client.call_tool("get_active_gates", json!({"risk_level": "low"}), 10);
    let high = client.call_tool("get_active_gates", json!({"risk_level": "high"}), 11);
    let low_active = low["gates"].as_array().unwrap().iter().filter(|g| g["active"] == true).count();
    let high_active = high["gates"].as_array().unwrap().iter().filter(|g| g["active"] == true).count();
    assert!(high_active > low_active, "high={high_active}, low={low_active}");
}

// ==========================================================================
// Layer 2: Contrast
// ==========================================================================

#[test]
fn contrast_black_on_white() {
    let mut client = McpClient::new();
    let result = client.call_tool("check_contrast", json!({"content": "#000000 #FFFFFF"}), 10);
    assert_eq!(result["ratio"], 21.0);
    assert_eq!(result["aa_normal"], true);
    assert_eq!(result["aaa_normal"], true);
}

// ==========================================================================
// Layer 2: Model Routing
// ==========================================================================

#[test]
fn model_for_security_audit_is_frontier() {
    let mut client = McpClient::new();
    let result = client.call_tool("get_model_for_task", json!({"query": "security_audit"}), 10);
    assert_eq!(result["tier"], "frontier");
}

// ==========================================================================
// Layer 2: Stubs
// ==========================================================================

#[test]
fn figma_stubs_fail_gracefully() {
    let mut client = McpClient::new();
    let result = client.call_tool("figma_get_tokens", json!({"query": "fake"}), 10);
    assert_eq!(result["success"], false);
}

#[test]
fn processor_stubs_return_defaults() {
    let mut client = McpClient::new();
    let result = client.call_tool("check_processor_thresholds", json!({}), 10);
    assert_eq!(result["corrections_exceeded"], false);
}

#[test]
fn audit_script_stubs_pass() {
    let mut client = McpClient::new();
    let result = client.call_tool("audit_script_8b", json!({"content": "echo hi"}), 10);
    assert_eq!(result["passed"], true);
}

// ==========================================================================
// Layer 2: Pipeline Config
// ==========================================================================

#[test]
fn pipeline_config_version() {
    let mut client = McpClient::new();
    let result = client.call_tool("get_pipeline_config", json!({}), 10);
    assert_eq!(result["metadata"]["version"], "2.0");
}

// ==========================================================================
// Layer 3: Error Handling
// ==========================================================================

#[test]
fn contrast_bad_input_returns_error() {
    let mut client = McpClient::new();
    let result = client.call_tool("check_contrast", json!({"content": "invalid"}), 10);
    assert!(result.get("error").is_some());
}

#[test]
fn register_bad_json_fails() {
    let mut client = McpClient::new();
    let result = client.call_tool("register_mcp_server", json!({"content": "not json"}), 10);
    assert_eq!(result["registered"], false);
}
