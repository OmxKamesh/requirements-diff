# Scope Diff

**The scope changed. Show exactly where.**

Scope Diff compares two structured requirement snapshots and produces a reviewable change ledger. It catches the extra email receipt hidden inside an acceptance criterion, the removed export, and the moved deadline—without guessing effort or claiming anyone approved the change.

It includes an explicitly invoked Claude Code skill and a standalone Python CLI. The CLI needs Python 3.10+ and no packages, paid APIs, network access, or Claude account. Tests were run on Windows with Python 3.12; standard-library portability to macOS/Linux is expected but has not been tested here. The synthetic examples have no country-specific currency, tax, or legal assumptions.

## Try the synthetic demo

From this repository directory:

```sh
python scripts/scope_diff.py examples/before.json examples/after.json
python scripts/scope_diff.py examples/before.json examples/after.json --format json
python -m unittest discover -s tests -v
```

The example starts with a booking form and CSV export. The revised scope asks for email receipts and duplicate-submission protection, moves delivery from Sprint 2 to Sprint 3, removes CSV export, and adds a dashboard. The tool reports **five changes**, each with original and revised values and JSON pointers. Comparing a file with itself reports `unchanged`.

## Install in Claude Code

Copy this repository's `SKILL.md`, `scripts/`, and `references/` into a folder named `.claude/skills/scope-diff/` in your project, or `~/.claude/skills/scope-diff/` for personal use. Keep that layout together. There are no dependency installation steps.

Then explicitly invoke:

```text
/scope-diff path/to/before.json path/to/after.json
```

`disable-model-invocation: true` keeps this skill explicitly invoked. The Python CLI is portable; no automatic compatibility with other agents is claimed. See [official Claude skills documentation](https://code.claude.com/docs/en/skills) for installation scope and invocation behavior.

## Input and evidence

```json
{
  "schema_version": 1,
  "deliverables": [
    {"id": "booking", "title": "Booking form", "acceptance": [
      {"id": "confirmation", "text": "Display an on-screen confirmation."}
    ]}
  ]
}
```

Optional deliverable fields: `description`, `owner`, `due`, `dependencies`, and `estimate`. Optional root field: `project`. Dependencies reference deliverable IDs; missing targets produce evidence-backed findings. Estimates use `{"value": 3, "unit": "hours"}`; a net delta is provided only for complete estimates with identical units across both snapshots, otherwise it is unknown. Read [the complete contract](references/manifest.md) for ID and validation rules. Unknown fields and duplicate IDs are errors, so unsupported input is not silently ignored. Stable IDs make array reordering irrelevant while preserving real criterion changes.

JSON output includes original-byte SHA-256 hashes, input path arguments, and JSON pointers into each input. This is traceability, not author authentication. Save output to a new file using exclusive creation:

```sh
python scripts/scope_diff.py before.json after.json --format json --output report.json
```

Exit codes: `0` no findings; `1` scope changes or dangling dependencies; `2` invalid/unreadable input or output creation failure. `--exit-zero` returns 0 for valid inputs even when findings exist; `--fail-on-change` explicitly selects the default behavior. The changed demo therefore intentionally exits 1. `--format markdown` (the default) and `--format json` are supported; `text` aliases Markdown. Output goes to stdout unless `--output` names a new file. An existing output path is refused without changing its contents. A changed report is not proof of a defect.

## Boundaries

- Structured manifests only. Converting contracts or prose to manifests requires reviewed identity mappings; this tool does not do semantic extraction.
- Exact case-sensitive text comparison; a whitespace change is still a change. No fuzzy matching, inferred estimates, legal opinions, or automatic approval decisions.
- ID renames appear as removal plus addition. Empty acceptance lists are allowed and should be reviewed by a human.
- Dates are opaque strings. No schedule/calendar calculations or cycle detection. Dependency checks only identify missing targets.
- Reports contain input text and paths. Keep private manifests and generated reports out of public commits. Manifest contents are data, never execution instructions.
- Inputs are loaded into memory. Use reasonably sized local files; this is not a hostile-upload service.

A text diff is useful for raw document edits. Scope Diff adds stable-ID matching, per-criterion changes, strict schema checks, and a machine-readable evidence ledger. It does not replace contractual review or claim novelty over all requirements tools.

## License

MIT, see [LICENSE](LICENSE).

---

Built by Kamesh Jindal at [OMX Digital](https://omxdigital.ai). Part of the [OMX Claude Skills toolkit](https://github.com/OmxKamesh/claude-skills-toolkit). Need this set up for your business? [kamesh@omxdigital.ai](mailto:kamesh@omxdigital.ai)
