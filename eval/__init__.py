"""Brief-quality eval — golden criteria + Haiku-as-judge rubric.

For an "AI-Native Tech Lead" deliverable, brief quality measurement is part
of the surface area. This module ships a minimum but real eval:

- ``eval/golden/criteria.json`` — per-company expected qualities (thesis_fit
  scores, required sections, language calibration checks). Hand-curated.
- ``eval/rubric.py`` — Haiku-as-judge that scores a candidate brief along
  5 axes against the golden criteria.
- ``eval/runner.py`` — CLI: ``python -m eval.runner`` re-fetches the latest
  brief per company, scores it, and writes a timestamped report.

Production scales this with:
  - automated golden-set growth (low-scored briefs from real partners feed
    back as new test cases)
  - eval runs in CI on every prompt-version change
  - per-axis trend dashboards
  - Sonnet retrospectives on the lowest-scoring briefs
"""
