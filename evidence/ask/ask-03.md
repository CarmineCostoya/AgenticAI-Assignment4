# ask-03 Evidence Card

- Captured: `2026-09-29T15:14:27+00:00`
- Mode: `ask`
- Execution: `local`
- Offline flag: `true`
- Model: `gemma3:1b-it-q4_K_M`
- Expected behavior: Explain the shift from volume payment toward quality, savings, downside risk, and population accountability.
- Expected sources: `["study-guide-2026", "reimbursement-value-2026-09-21"]`
- Expected locators: `["slides 8-14"]`

## Question

How does moving from fee-for-service toward value-based payment change provider accountability?

## Retrieved Original Passages

### S1: `vault/raw/course-slides/MBA297A_Reimbursement__Value_09.21.26posted.pdf` — slide 11

Score: `33.284776`; query coverage: `11`

> Plan was to move incrementally to advanced forms,
> increasing accountability for cost and quality
> • Goal hasn’t been that
> system would fully move to
> Category 4
> • Many can’t but the goal
> has been to get away
> from FFS category
> • Huge concern for many with
> taking on risk for cost and
> quality and not being able
> to deliver
> • Reasons/risks often out
> of their control
> • Harm dynamics with
> patients
> • Suffer financial losses
> that would be hard to
> recover from 11

### S2: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "September 21 Reimbursement and value"

Score: `23.168125`; query coverage: `11`

> This session connects the money stack to the care journey. Payment signals influence whether products and services exist, where care occurs, which activities clinicians prioritize, and whether organizations invest in data or coordination. Fee-for-service remains dominant because it is simple, deeply embedded, and economically important to incumbents. Value-based models increase accountability for cost and quality but require capabilities and expose organizations to risks they may not control. Value varies by stakeholder, situation, time horizon, and urgency, making standardized payment difficult. Most providers operate in a hybrid environment and will continue to earn under both volume and value models. Public programs often pilot new models first; private organizations adopt, adapt, or invest around those policy signals.

### S3: `vault/raw/course-slides/MBA297A_Reimbursement__Value_09.21.26posted.pdf` — slide 8

Score: `17.755100`; query coverage: `6`

> Volume Based or Fee-for-Service Has Been Dominant
> Payment Model for Decades
> • FFS is a straight-forward way of
> paying for healthcare that’s
> embedded across the majority
> of health system processes and
> data flows – used in US and
> many other countries
> • Called out for being anchored to
> the volume of care and
> potentially incentivizing more
> care/product is provided vs an
> optimal amount- not linked to
> outcomes, impact or value
> 8

### S4: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "A practical test for value-based arrangements"

Score: `17.388869`; query coverage: `6`

> Define the population, covered services, time horizon, and accountable entity. Specify outcomes that matter clinically and to patients, not only easily reported process measures. Set a cost benchmark that the accountable organization can influence and understand. Match downside risk to the organization's capital, data, scale, authority, and clinical capabilities. Check for incentives to avoid high-risk patients, withhold useful care, or shift cost outside the measured scope. Evaluate whether the model can coexist with the organization's remaining fee-for-service business.

### S5: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "6 Why can a hospital feel pulled in two directions under value-based care?"

Score: `16.959855`; query coverage: `6`

> Avoiding an admission can generate shared savings under a population contract while eliminating fee-for-service revenue from the hospital. Hybrid payment creates simultaneous incentives to reduce and preserve volume. [Class 9/21/26; McKinsey, 2019]

## Actual Displayed Answer

Moving from fee-for-service to value-based payment changes provider accountability by increasing accountability for cost and quality. [S1 — vault/raw/course-slides/MBA297A_Reimbursement__Value_09.21.26posted.pdf, slide 11]

Value-based models increase accountability for cost and quality, but require capabilities and expose organizations to risks they may not control. [S2 — vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx, section "September 21 Reimbursement and value"]

## Raw Gemma Output

```json
{
  "support_check": {
    "relevant_evidence_ids": [
      "S1",
      "S2",
      "S3",
      "S4",
      "S5"
    ],
    "reason": "The passages discuss the shift from fee-for-service to value-based payment, focusing on accountability, risk, and outcomes. They detail the challenges of transitioning to a new payment model, including the need for organizations to define populations, services, time horizons, and accountability, and"
  },
  "answer": {
    "claims": [
      {
        "text": "Moving from fee-for-service to value-based payment changes provider accountability by increasing accountability for cost and quality.",
        "evidence_ids": [
          "S1"
        ]
      },
      {
        "text": "Value-based models increase accountability for cost and quality, but require capabilities and expose organizations to risks they may not control.",
        "evidence_ids": [
          "S2"
        ]
      }
    ]
  }
}
```

## Run Metrics

```json
{
  "generated_tokens": 228,
  "load_duration_seconds": 0.002,
  "model_size_mb": 838.51,
  "model_vram_mb": 838.51,
  "ollama_rss_mb": 1099.34,
  "prompt_tokens": 2351,
  "total_duration_seconds": 6.921,
  "wall_seconds": 6.926
}
```

## Assessment

- Automated structural assessment: **PASS**
- Retrieved source IDs: `["reimbursement-value-2026-09-21", "study-guide-2026"]`
- Citation validation: `passed`
- Human claim-to-passage review: `PASS — slide 11 (S1) and the study guide (S2) directly support increased accountability for cost and quality, along with the capabilities and risk required under value-based payment.`
- Notes: The passages discuss the shift from fee-for-service to value-based payment, focusing on accountability, risk, and outcomes. They detail the challenges of transitioning to a new payment model, including the need for organizations to define populations, services, time horizons, and accountability, and
