# Worked digest example

These small, synthetic Pa11y CI-shaped reports demonstrate the output without
scanning a live website. Messages are illustrative, not copied scanner output.
The `.test` URLs do not represent an audited site.

Compare the raw [desktop JSON](desktop.json) and [mobile JSON](mobile.json)
with the [combined Markdown digest](audit.md).

| Scenario in the raw inputs | What the digest shows |
| --- | --- |
| Header image finding on two pages and both viewports | One rule group, with each occurrence and run retained |
| Separate product image with the same rule | A separate selector inside that group; potentially a separate fix |
| About page succeeds on desktop but fails on mobile | Desktop findings remain; mobile coverage failure is explicit |
| Contact page has no findings | Counts as a successful check |
| Offline page only fails | Excluded from successful URL and finding counts |

Expected totals: **3 unique URLs successfully tested, 4 successful page checks,
2 failed page checks, 4 finding occurrences, 1 rule group.** There are 4 distinct
URLs attempted across the two reports. Occurrences are not unique fixes.

Regenerate from the repository root (only the generation timestamp varies):

```bash
python3 scripts/pa11y_digest.py \
  desktop=examples/digest/desktop.json \
  mobile=examples/digest/mobile.json \
  --out examples/digest/audit.md
```

The `WCAG2AA` prefix is the test standard, not the individual criterion's level
or severity. IDs can assist comparisons with consistent labels and selectors;
the digest does not perform baseline comparison or detect regressions.

This example demonstrates the existing Python postprocessor. Adoption as a
Pa11y CI reporter would require a JavaScript implementation and agreement on
how to handle multiple independent runs.
