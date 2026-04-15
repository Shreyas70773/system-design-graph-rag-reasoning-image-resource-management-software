# Red-Team Conditional Pass Closure Checklist

Date: April 12, 2026
Status: Open
Goal: Close all Critical and High blockers before implementation lock.

## 1. Current Verdict

Executive verdict: Conditional Pass.

Go is allowed only after all Critical and High findings are closed with evidence artifacts.

---

## 2. Blocker Closure Matrix

| Blocker ID | Severity | Finding | Required Fix | Evidence Artifact | Owner | Due Date | Status |
|---|---|---|---|---|---|---|---|
| B1 | Critical | Paired design tested with independent-sample method | Use Wilcoxon signed-rank for pairwise paired comparisons; use Friedman + corrected post-hoc for 3+ paired methods | `stats_protocol_v1.md` + test script output | Methods and Statistics Lead | TBD | Open |
| B2 | High | VRAM collision risk with SD 3.5 + dense decode guidance | Replace per-step full decode color loss with sparse decode or latent proxy; profile memory envelopes | `vram_profile_report.md` + run logs | Systems and Performance Lead | TBD | Open |
| B3 | High | Unverified numeric gains from unrelated methods | Remove borrowed gains; relabel as hypothesis until measured | `claim_ledger.csv` with citation mapping | Evidence and Claims Lead | TBD | Open |
| B4 | Medium | Identity module license risk | Create license matrix; mark research-only tools or replace with permissible alternatives | `license_matrix.md` | Compliance and Licensing Lead | TBD | Open |

### 2.1 Owner Role Map

1. B1 owner (Methods and Statistics Lead): Owns protocol correctness, test implementation, and final analysis reproducibility.
2. B2 owner (Systems and Performance Lead): Owns runtime profiling, memory envelopes, and fallback configuration safety.
3. B3 owner (Evidence and Claims Lead): Owns claim-to-citation traceability and removal of unsupported numeric claims.
4. B4 owner (Compliance and Licensing Lead): Owns dependency license classification and usage-scope approvals.

---

## 3. Mandatory Artifacts to Produce

1. `docs/stats_protocol_v1.md`
- Define paired design formally.
- State Wilcoxon signed-rank for paired pairwise tests.
- State Friedman for multi-method paired tests.
- Include effect size and confidence interval rules.

2. `docs/vram_profile_report.md`
- Record model, resolution, sampler, steps, precision, adapter stack.
- Report peak VRAM for baseline and controlled variants.
- Report failure threshold and fallback configuration.

3. `docs/claim_ledger.csv`
- Columns: claim_id, claim_text, source_url, source_tier, confidence, status.
- Any claim without a valid citation is rejected.

4. `docs/license_matrix.md`
- Columns: dependency, license, usage scope, restrictions, decision, replacement.
- Highlight non-commercial constraints explicitly.

---

## 4. Verification Rules

1. No method comparison result is accepted without paired-run parity:
- same prompt
- same seed
- same resolution and steps where applicable

2. No statistical claim is accepted without:
- named test
- effect size
- confidence interval
- correction for multiple comparisons when needed

3. No performance claim is accepted without:
- hardware profile
- run configuration
- reproducible log reference

4. No dependency enters production path without license classification.

---

## 5. Go or No-Go Gate

Go criteria:
1. B1 closed with statistical protocol evidence.
2. B2 closed with VRAM profile evidence.
3. B3 closed with claim ledger evidence.
4. All High and Critical blockers marked Closed.

No-Go criteria:
1. Any Critical blocker remains Open.
2. Any core claim lacks citation mapping.
3. Any paired-analysis section still uses independent-sample tests.

---

## 6. Immediate 72-Hour Execution Plan

Day 1:
1. Freeze stats protocol and publish `stats_protocol_v1.md`.
2. Build claim ledger template and backfill current claims.

Day 2:
1. Run VRAM profiling matrix for baseline and guided variants.
2. Record sparse decode fallback thresholds.

Day 3:
1. Finalize license matrix and mark restricted dependencies.
2. Hold closure review and update blocker statuses.

---

This checklist operationalizes red-team findings into objective closure tasks and measurable evidence artifacts.