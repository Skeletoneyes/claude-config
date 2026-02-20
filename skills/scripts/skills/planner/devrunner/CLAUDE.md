# devrunner/

Artifact-based test verification workflow: brief authoring, artifact analysis, iteration constants.

## Index

| File | Contents (WHAT) | Read When (WHEN) |
| --- | --- | --- |
| `constants.py` | DEVRUNNER_ITERATION_LIMIT, DEVRUNNER_ITERATION_DEFAULT, get_devrunner_blocking_severities(), get_devrunner_iteration_guidance(), BRIEF_SCHEMA_FIELDS | Modifying iteration limits, de-escalation thresholds, or brief.json schema |
| `brief_author.py` | 3-step workflow: read plan criteria, read manifest, author brief.json with severity-tagged claims | Understanding brief authoring dispatch, modifying claim authoring guidance |
| `analysis.py` | 4-step workflow: read brief, read manifest, examine artifacts, report verdict; --blocking-severities CLI arg | Understanding artifact analysis dispatch, modifying verdict rules or dual-filter model |
| `README.md` | Trust boundary rationale, workflow steps, executor integration, dual-filter model, error handling | Understanding DevRunner architecture or design decisions |
