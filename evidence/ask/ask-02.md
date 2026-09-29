# ask-02 Evidence Card

- Captured: `2026-09-29T15:14:20+00:00`
- Mode: `ask`
- Execution: `local`
- Offline flag: `true`
- Model: `gemma3:1b-it-q4_K_M`
- Expected behavior: Explain that approval is distinct from coverage, reimbursement, adoption, and affordability.
- Expected sources: `["study-guide-2026", "reimbursement-value-2026-09-21"]`
- Expected locators: `["slide 6"]`

## Question

Why can an approved healthcare product still fail to reach a patient?

## Retrieved Original Passages

### S1: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "Coverage is not the same as access"

Score: `45.973967`; query coverage: `13`

> Insurance can protect assets and make payment more predictable, but a coverage card does not guarantee a usable clinician network, an affordable deductible, a place on a formulary, an available appointment, or reimbursement for a new technology. Regulatory approval, coverage, reimbursement, provider adoption, and patient affordability are separate gates. True access requires passage through all of them. [Class 9/2/26; Class 9/21/26]

### S2: `vault/raw/course-slides/MBA297A_Reimbursement__Value_09.21.26posted.pdf` — slide 6

Score: `36.268492`; query coverage: `18`

> Reimbursement is big hurdle along road to true access
> of a service or product – who will pay and how much?
> • Just because it exists, doesn’t mean
> Covered
> Medically
> a sponsor will pay for it (or for all of Benefit
> necessary
> it or in all cases)
> Different issues w/ legacy services and
> ▪
> Low vs
> products vs innovative, newer ones
> High Value
> ▪ Does system already have a way to pay or Experimental
> Care
> need new model, code, pathway?
> • Capital is essential to develop new
> On/Off
> products, services, expand health
> Coverage Formulary
> footprint, so investors expect that with
> Evidence
> products/services can generate Site of Care
> Development
> Neutrality
> revenue – key part of business plan
> 6

### S3: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "7 What turns coverage into true access?"

Score: `22.587146`; query coverage: `5`

> The benefit must include the service, the patient must find an available participating provider, reimbursement must support delivery, required approvals must be attainable, and the remaining cost must be affordable. A coverage decision is necessary but often insufficient. [Class 9/21/26]

### S4: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "August 24 Course introduction and knowledge check"

Score: `21.936358`; query coverage: `9`

> The opening session establishes the course's purpose: develop a working understanding of healthcare structure, financing, stakeholders, trends, and innovation so that students can form defensible points of view. The principles emphasize unavoidable tradeoffs, the power and limits of financial incentives, tension between innovation and near-term cost control, inequitable outcomes, and the importance of learning from other sectors and countries. Healthcare is larger than medical care; social, behavioral, and environmental determinants shape health. Regulatory approval is only one hurdle for innovation. Coverage, reimbursement, workflow adoption, and affordability also matter. The knowledge check previews recurring issues: federal spending, drug pricing, hospital margins, obesity and GLP-1s, medical affordability, AI, direct channels, and underused data.

### S5: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "Questions for analyzing any healthcare business or policy"

Score: `21.373257`; query coverage: `12`

> Who is the patient or population, and what health problem is being addressed? Who sponsors the care, who pays claims, and who ultimately bears financial risk? What coverage, reimbursement, regulatory, evidence, and workflow gates must be crossed? Which intermediaries control information, distribution, networks, formularies, or purchasing power? What behavior does the payment model reward, and what unintended behavior might it create? Does the proposal reduce total cost or merely shift it? Who gains economic value, who loses it, and who has the power to block change? What evidence would show better access, experience, equity, quality, and outcomes?

## Actual Displayed Answer

Regulatory approval, coverage, reimbursement, provider adoption, and patient affordability are separate gates. [S1 — vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx, section "Coverage is not the same as access"]

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
    "reason": "The passages discuss the multiple gates and requirements for true access to healthcare services, including coverage, reimbursement, provider adoption, and affordability. They highlight that simply existing doesn't guarantee access."
  },
  "answer": {
    "claims": [
      {
        "text": "Regulatory approval, coverage, reimbursement, provider adoption, and patient affordability are separate gates.",
        "evidence_ids": [
          "S1"
        ]
      }
    ]
  }
}
```

## Run Metrics

```json
{
  "generated_tokens": 142,
  "load_duration_seconds": 0.004,
  "model_size_mb": 838.51,
  "model_vram_mb": 838.51,
  "ollama_rss_mb": 1091.94,
  "prompt_tokens": 2480,
  "total_duration_seconds": 5.488,
  "wall_seconds": 5.492
}
```

## Assessment

- Automated structural assessment: **PASS**
- Retrieved source IDs: `["reimbursement-value-2026-09-21", "study-guide-2026"]`
- Citation validation: `passed`
- Human claim-to-passage review: `PASS — S1 directly identifies regulatory approval, coverage, reimbursement, provider adoption, and affordability as separate access gates; the Sep. 21 deck independently supports the access barrier in the retrieved packet.`
- Notes: The passages discuss the multiple gates and requirements for true access to healthcare services, including coverage, reimbursement, provider adoption, and affordability. They highlight that simply existing doesn't guarantee access.
