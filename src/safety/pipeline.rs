//! Pipeline configuration — gate activation per mode/risk level.

use super::RiskLevel;
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct PipelineConfig {
    pub gates: Vec<GateConfig>,
}

#[derive(Debug, Serialize)]
pub struct GateConfig {
    pub gate: u8,
    pub name: String,
    pub active: bool,
}

/// Get active gates for a given risk level.
pub fn active_gates(risk: RiskLevel) -> Vec<u8> {
    match risk {
        RiskLevel::Low => vec![1, 6],
        RiskLevel::Medium => vec![1, 2, 3, 4, 6, 7],
        RiskLevel::High => vec![1, 2, 3, 4, 5, 6, 7],
    }
}

pub fn gate_name(gate: u8) -> &'static str {
    match gate {
        1 => "Preflight",
        2 => "TDD",
        3 => "Security Audit",
        4 => "8B Adversarial",
        5 => "32B Second Opinion",
        6 => "Human Approval",
        7 => "DRY_RUN",
        _ => "Unknown",
    }
}

pub fn get_config(risk: RiskLevel) -> PipelineConfig {
    let active = active_gates(risk);
    let gates = (1..=7)
        .map(|g| GateConfig {
            gate: g,
            name: gate_name(g).into(),
            active: active.contains(&g),
        })
        .collect();
    PipelineConfig { gates }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn low_risk_two_gates() {
        let gates = active_gates(RiskLevel::Low);
        assert_eq!(gates, vec![1, 6]);
    }

    #[test]
    fn high_risk_all_gates() {
        let gates = active_gates(RiskLevel::High);
        assert_eq!(gates, vec![1, 2, 3, 4, 5, 6, 7]);
    }

    #[test]
    fn config_has_all_seven() {
        let config = get_config(RiskLevel::Medium);
        assert_eq!(config.gates.len(), 7);
    }
}
