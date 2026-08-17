# Pacific Dataviz Challenge 2026 — submission pack

This folder contains the locally verified evidence pack for the interactive page:

- `fallback.html`, `fallback.pdf` and `fallback.png` — static fallbacks;
- `problem-statement.md` — the question and the visual response;
- `ai-disclosure.md` — prepared AI-use disclosure text;
- `checklist.md` — official requirements and entrant-owned release gates;
- `build-environment.txt` — Python, WeasyPrint and Poppler versions used for the fallback;
- `pacific-dataviz-2026-release.zip` — packaged source and evidence.

The evidence files are also available directly: [problem statement](problem-statement.md), [AI disclosure](ai-disclosure.md), [submission checklist](checklist.md), and [data dictionary](../data/data_dictionary.md).

The interactive entry point is `../src/`. The page, local CSV snapshot, data dictionary and fetch script are intentionally shipped together so the evidence trail can be inspected without a live API request.

## Published URL

The interactive page is published at <https://csmar432.github.io/pacific-dataviz-2026/src/> through public GitHub Pages with HTTPS enforced. The URL was checked without authentication on 17 August 2026; keep the repository public and unchanged through 31 August 2029.

Before official submission, the entrant must add the real creator/team details, verify the current dataset-specific licences and attribution, test logged-out access, and complete the registration before the deadline in the official rules.

The local working folder also contains `DELIVERY.md`. That mutable verification report is intentionally excluded from the release ZIP so rerunning verification cannot invalidate the archive it just checked.
