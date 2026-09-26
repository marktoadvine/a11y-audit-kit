# Illustrative agent handoff

This is a hand-authored example based on the synthetic JSON fixtures, not an
agent execution transcript or a verified audit. It shows what a useful final
handoff should contain after following the canonical procedure.

## Coverage first

The [digest](audit.md) contains 4 successful page checks across desktop/mobile,
covering 3 distinct URLs. There are 4 finding occurrences in one rule group.

Two mobile checks failed: `/about` and `/offline`. `/about` has desktop evidence
only; `/offline` has no successful coverage. These failures are not clean passes.
Resolve the access problems and rerun before treating the requested coverage as
complete. No browser verification or source-code inspection has been performed
for this synthetic example.

## Candidate draft: review header-logo alternative text

- **Evidence:** `f137808cf267` (desktop home), `5ef3ab54d9e9` (desktop about),
  `33ffaf8ff437` (mobile home). Selector: `#header-logo`.
- **Reported criterion:** 1.1.1, Non-text Content.
- **Potential impact:** the image may lack an appropriate text alternative.
  Whether it is informative, functional, or decorative requires review.
- **Grouping assumption:** the matching selector suggests a shared component;
  it does not prove one. Check the implementation before treating this as one fix.
- **Proposed review:** inspect image purpose, surrounding text, any link's
  accessible name, and existing alternatives. Choose contextual alternative
  text or decorative treatment as appropriate; do not invent an alt string
  from the selector alone.
- **Acceptance checks:** verify the intended accessible name/alternative on
  affected pages and viewports; rerun the scanner after the change. Recover the
  failed mobile about check before claiming it is covered.
- **Priority:** provisional pending purpose and task-impact review.

## Separate candidate draft: review product-image alternative text

- **Evidence:** `fa6b52dfca1c` (desktop home), selector `#product-photo`.
- **Reported criterion:** 1.1.1, Non-text Content.
- **Reason to separate:** this is a different image from the header logo;
  sharing a rule does not establish a shared fix.
- **Proposed review:** inspect what product information the image conveys and
  whether adjacent content already supplies an equivalent alternative.
- **Acceptance checks:** confirm the chosen alternative in context and rerun
  the desktop scan. Absence from the mobile fixture does not prove that image
  is accessible, present, or tested in every mobile state.
- **Priority:** provisional pending purpose and task-impact review.

## Still needed

- Verify actual pages, image purposes, component ownership, and user impact.
- Resolve failed checks; manually review keyboard interaction, focus behavior,
  and other aspects not settled by these automated findings.
- Review these drafts before filing anything. No tickets have been created.

The distinction is intentional: the script preserves and organizes evidence;
the agent proposes an interpretation; a reviewer confirms the work.
