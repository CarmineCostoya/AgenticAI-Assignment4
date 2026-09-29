# ask-01 Evidence Card

- Captured: `2026-09-29T15:14:15+00:00`
- Mode: `ask`
- Execution: `local`
- Offline flag: `true`
- Model: `gemma3:1b-it-q4_K_M`
- Expected behavior: Give a grounded list of comparison dimensions.
- Expected sources: `["study-guide-2026", "structure-costs-2026-08-31"]`
- Expected locators: `["slide 3"]`

## Question

Which dimensions do the course materials use to compare health systems?

## Retrieved Original Passages

### S1: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "August 31 Health-system structure, costs, and comparison"

Score: `36.445929`; query coverage: `15`

> This session supplies the comparison framework: government role, coverage and financing, benefits, delivery organization, payment, cost containment, affordability, equity, technology, quality, and outcomes. The US system appears complicated, fragmented, expensive, inequitable, innovative, and oriented more toward medical care than health. International benchmarking helps reveal the consequences of structural choices without pretending that another country's model can be copied intact.

### S2: `vault/raw/course-slides/MBA297A_Structure_Costs_Value_08.31.26.pdf` — slide 3

Score: `30.317563`; query coverage: `11`

> Dimensions Often Used to Understand & Compare
> Health Systems
> • Role of government
> • Who is covered and how is care financed?
> • What is covered (services, products) and under what
> conditions. Where is the NO?
> • How is the delivery system organized and financed/paid?
> • How are costs contained? Is care affordable?
> • How important is equity, access? How try to achieve?
> • How are new technologies deployed, used?
> • How is quality measured, promoted?
> • What are the system’s outcomes in terms of health,
> access, equity, cost, efficiency, innovation, etc?
> 3

### S3: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "7 What turns coverage into true access?"

Score: `17.115050`; query coverage: `4`

> The benefit must include the service, the patient must find an available participating provider, reimbursement must support delivery, required approvals must be attainable, and the remaining cost must be affordable. A coverage decision is necessary but often insufficient. [Class 9/21/26]

### S4: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "August 24 Course introduction and knowledge check"

Score: `16.786849`; query coverage: `10`

> The opening session establishes the course's purpose: develop a working understanding of healthcare structure, financing, stakeholders, trends, and innovation so that students can form defensible points of view. The principles emphasize unavoidable tradeoffs, the power and limits of financial incentives, tension between innovation and near-term cost control, inequitable outcomes, and the importance of learning from other sectors and countries. Healthcare is larger than medical care; social, behavioral, and environmental determinants shape health. Regulatory approval is only one hurdle for innovation. Coverage, reimbursement, workflow adoption, and affordability also matter. The knowledge check previews recurring issues: federal spending, drug pricing, hospital margins, obesity and GLP-1s, medical affordability, AI, direct channels, and underused data.

### S5: `vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx` — section "Coverage is not the same as access"

Score: `16.028093`; query coverage: `6`

> Insurance can protect assets and make payment more predictable, but a coverage card does not guarantee a usable clinician network, an affordable deductible, a place on a formulary, an available appointment, or reimbursement for a new technology. Regulatory approval, coverage, reimbursement, provider adoption, and patient affordability are separate gates. True access requires passage through all of them. [Class 9/2/26; Class 9/21/26]

## Actual Displayed Answer

Role of government, coverage and financing, benefits, delivery organization, payment, cost containment, affordability, equity, technology, quality, and outcomes [S1 — vault/raw/study-guide/Healthcare in the 21st Century Study Guide through September 21 2026.docx, section "August 31 Health-system structure, costs, and comparison"]

## Raw Gemma Output

```json
{
  "support_check": {
    "relevant_evidence_ids": [
      "S1",
      "S2"
    ],
    "reason": "The passages discuss dimensions used to compare health systems, specifically the role of government, coverage, financing, benefits, delivery organization, payment, cost containment, equity, technology, quality, and outcomes.  These dimensions are presented in the text."
  },
  "answer": {
    "claims": [
      {
        "text": "Role of government, coverage and financing, benefits, delivery organization, payment, cost containment, affordability, equity, technology, quality, and outcomes",
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
  "generated_tokens": 130,
  "load_duration_seconds": 1.878,
  "model_size_mb": 838.51,
  "model_vram_mb": 838.51,
  "ollama_rss_mb": 1134.44,
  "prompt_tokens": 1894,
  "total_duration_seconds": 6.621,
  "wall_seconds": 6.628
}
```

## Assessment

- Automated structural assessment: **PASS**
- Retrieved source IDs: `["structure-costs-2026-08-31", "study-guide-2026"]`
- Citation validation: `passed`
- Human claim-to-passage review: `PASS — the complete comparison list is stated directly in S1 and independently mirrored by the Aug. 31 deck on slide 3 (S2).`
- Notes: The passages discuss dimensions used to compare health systems, specifically the role of government, coverage, financing, benefits, delivery organization, payment, cost containment, equity, technology, quality, and outcomes.  These dimensions are presented in the text.
