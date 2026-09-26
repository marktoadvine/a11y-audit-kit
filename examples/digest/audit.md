# Pa11y Accessibility Audit Digest

- **Generated:** 2026-09-25 18:37 EDT
- **Unique URLs successfully tested:** 3
- **Successful page checks (across runs):** 4
- **Pages with findings:** 2
- **Finding occurrences (across runs):** 4 (errors 4, warnings 0, notices 0)
- **Distinct rules:** 1
- **Failed page checks (across runs):** 2

### Sources

| Run | Report file | Pages | Passes | Errors |
| --- | --- | --- | --- | --- |
| desktop | `examples/digest/desktop.json` | 3 | 1 | 2 |
| mobile | `examples/digest/mobile.json` | 3 | 0 | 3 |

> Automated findings are a starting point, not a final accessibility decision. Confirm each one in a browser and verify against WCAG 2.2 before creating or closing remediation work.

## Failed page checks

These URL/run combinations were not successfully audited and are excluded from successful-check and finding counts. A URL may have succeeded in another run. Resolve these errors and rerun before treating coverage as complete.

| Run | URL | Error |
| --- | --- | --- |
| mobile | https://example.test/about | Synthetic navigation timeout |
| mobile | https://example.test/offline | Synthetic connection failure |

## Summary by rule

Each row groups a rule for review, not a confirmed ticket or unique fix.
Occurrences from every run are retained and counted; they are not deduplicated.
The standard prefix is not a severity rating or the criterion's conformance level.
IDs repeat only while rule, run label, URL and selector stay unchanged;
they do not detect new, resolved or reopened issues automatically.

| Rule | Standard prefix | SC | Type | Occurrences | Pages | Runs |
| --- | --- | --- | --- | --- | --- | --- |
| `WCAG2AA.Principle1.Guideline1_1.1_1_1.H37` | AA | 1.1.1 | error | 4 | 2 | desktop, mobile |

## Findings by rule

### 1.1.1 — 4 finding(s) on 2 page(s)

- **Rule:** `WCAG2AA.Principle1.Guideline1_1.1_1_1.H37`
- **Type:** error
- **Standard prefix:** WCAG 2 AA
- **Success criterion:** 1.1.1
- **Technique:** H37
- **Runs affected:** desktop, mobile
- **Pages affected:** https://example.test/, https://example.test/about

<details><summary>Occurrences</summary>

- `f137808cf267` **desktop** https://example.test/
  - Selector: `#header-logo`
  - Message: Synthetic example: image needs alternative text.
  - Context: `<img src="example.png">`
- `fa6b52dfca1c` **desktop** https://example.test/
  - Selector: `#product-photo`
  - Message: Synthetic example: image needs alternative text.
  - Context: `<img src="example.png">`
- `5ef3ab54d9e9` **desktop** https://example.test/about
  - Selector: `#header-logo`
  - Message: Synthetic example: image needs alternative text.
  - Context: `<img src="example.png">`
- `33ffaf8ff437` **mobile** https://example.test/
  - Selector: `#header-logo`
  - Message: Synthetic example: image needs alternative text.
  - Context: `<img src="example.png">`

</details>

## Findings by page

### https://example.test/

3 finding(s)

- `f137808cf267` [error] SC 1.1.1 (`WCAG2AA.Principle1.Guideline1_1.1_1_1.H37`) — desktop
  - Selector: `#header-logo`
- `fa6b52dfca1c` [error] SC 1.1.1 (`WCAG2AA.Principle1.Guideline1_1.1_1_1.H37`) — desktop
  - Selector: `#product-photo`
- `33ffaf8ff437` [error] SC 1.1.1 (`WCAG2AA.Principle1.Guideline1_1.1_1_1.H37`) — mobile
  - Selector: `#header-logo`

### https://example.test/about

1 finding(s)

- `5ef3ab54d9e9` [error] SC 1.1.1 (`WCAG2AA.Principle1.Guideline1_1.1_1_1.H37`) — desktop
  - Selector: `#header-logo`
