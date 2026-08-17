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

Before official submission, the entrant must add the real creator/team details, verify the current dataset-specific licences and attribution, publish the interactive page at a stable public HTTPS URL, test logged-out access, and complete the registration before the deadline in the official rules.

The local working folder also contains `DELIVERY.md`. That mutable verification report is intentionally excluded from the release ZIP so rerunning verification cannot invalidate the archive it just checked.
