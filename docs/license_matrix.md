# Dependency License Matrix and Identity-Module Policy

Date: April 12, 2026
Project: Brand-Aligned GraphRAG Visual Synthesis
Status: Active Policy

## 1. Purpose

Track dependency licenses and enforce allowed usage scope for research and deployment.

## 2. Identity-Module Policy

### 2.1 Policy Objective
Enable identity consistency experiments without creating legal exposure or scope confusion.

### 2.2 Two-Track Policy
1. Research track:
- Restricted tools may be used only for academic proof-of-concept.
- Outputs must be labeled Research Use Only.

2. Deployment track:
- Only permissive/commercially compatible dependencies are allowed.
- Any restricted dependency must be replaced before production demos marketed as enterprise-ready.

### 2.3 Decision Rules
1. If license is non-commercial or unclear, classify as Restricted.
2. Restricted dependencies cannot be part of deployment path.
3. Every identity dependency must record:
- license text link
- allowed scope
- restriction summary
- approved decision

### 2.4 Recommended Default
- Default to permissive identity path where feasible.
- Keep restricted path only as optional research ablation.

## 3. License Classification Table

| dependency | module_scope | license | usage_scope | restriction_risk | decision | replacement | evidence_link |
|---|---|---|---|---|---|---|---|
| Stable Diffusion 3.5 Medium | base model | Stability AI Community License | research only | medium | research_only | SDXL base path for deployment | docs/license_policy.json |
| Neo4j Python Driver | graph retrieval | Apache 2.0 | broad | low | allowed | n/a | docs/license_policy.json |
| Kornia | color regularizer | Apache 2.0 | broad | low | allowed | n/a | docs/license_policy.json |
| InsightFace or PuLID path | identity module | restrictive or non-commercial terms | research only | high | research_only | histogram-proxy or permissive identity path | docs/license_policy.json |
| InstantID-compatible stack | identity module alternative | mixed component licenses | research only until legal verification | medium | research_only | deployment path blocked until full verification | docs/license_policy.json |

## 4. Compliance Workflow

1. Add dependency row before first use.
2. Classify risk level and usage scope.
3. Review by compliance owner and project lead.
4. Mark final decision: allowed, research_only, blocked.
5. Revalidate before external demo or release.

## 5. Ownership

B4 Owner (License and Compliance): Compliance Owner
Approver: Project Lead
Deadline: 2026-04-12

## 6. Notes

This matrix controls technical choices for the identity module and ensures research claims do not imply deployment rights where licenses do not permit them.

## 7. Enforcement

Automated check script:
- `backend/scripts/check_license_compliance.py`

Machine-readable policy:
- `docs/license_policy.json`

Generated compliance artifact:
- `docs/artifacts/license_compliance_report.json`
