# Offline Evaluation Harness Results

**Execution Timestamp**: 2026-09-19 17:36:09 UTC
**Evaluated Schemes**: 10
**Tested Personas**: 5
**Ground Truth Checks**: 9

## Summary Metrics

| Metric | Target | Measured Value | Status |
| :--- | :---: | :---: | :---: |
| **Precision@5** | ≥ 0.80 | **0.80** | ✅ PASS |
| **Eligibility Accuracy** | ≥ 90.0% | **100.0%** | ✅ PASS |
| **Avg Latency per Persona** | < 100 ms | **1.98 ms** | ✅ PASS |

**Overall Benchmark Status**: **PASSED**

## Persona Detailed Breakdown

| Persona ID | Name | Precision@5 | Accuracy | Latency (ms) | Top Recommended Scheme | Top Status |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| `P1` | Ramesh Kamble (SC Student) | 1.0 | 100.0% | 2.34 ms | 4th Floor, NeGD, Electronics Niketan, 6 CGO Complex, Lodhi Road, New Delhi - 110003, India | `potentially_relevant` |
| `P2` | Sanjay Patil (Small Farmer) | 1.0 | 100.0% | 1.79 ms | 4th Floor, NeGD, Electronics Niketan, 6 CGO Complex, Lodhi Road, New Delhi - 110003, India | `potentially_relevant` |
| `P3` | Priya Deshmukh (EWS Student) | 1.0 | 100.0% | 2.84 ms | 4th Floor, NeGD, Electronics Niketan, 6 CGO Complex, Lodhi Road, New Delhi - 110003, India | `potentially_relevant` |
| `P4` | Vikram Mehta (High Income Exec) | 1.0 | 100.0% | 1.66 ms | 4th Floor, NeGD, Electronics Niketan, 6 CGO Complex, Lodhi Road, New Delhi - 110003, India | `not_matching` |
| `P5` | Shantabai More (Senior Citizen) | 0.0 | 100.0% | 1.29 ms | 4th Floor, NeGD, Electronics Niketan, 6 CGO Complex, Lodhi Road, New Delhi - 110003, India | `potentially_relevant` |

## Evaluation Grounding Verification
- **Deterministic Engine**: Matching evaluation logic executes pure Python criteria (`app.services.matching`). Zero non-deterministic LLM variance during matching.
- **Status Classification**: Rules are enforced strictly (`not_matching` on any required rule failure, `cannot_determine` on unknown inputs, `potentially_relevant` on complete rule compliance).
- **Guardrail Checks**: LLM explanations generated for top ranked schemes passed number and date fact verification.