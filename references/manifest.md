# Manifest contract (v1)

Root fields: `schema_version` (integer 1), `deliverables` (array), optional `project` (nonempty string). Unknown fields are rejected to prevent silent omission.

Each deliverable requires `id`, `title`, and `acceptance`; optional fields are `description`, `owner`, `due`, `dependencies`, and `estimate`. Text fields must be nonempty strings. Dates are opaque strings, not parsed schedules. Each acceptance entry requires exactly `id` and `text`.

`dependencies` is an array of unique deliverable IDs; ordering is ignored. Missing targets are reported as findings with pointers in either snapshot, rather than suppressing the comparison. Self-dependencies and cycles are not analyzed.

`estimate` is an object with exactly `value` (nonnegative integer) and `unit` (nonempty string), for example `{"value": 3, "unit": "hours"}`. A net after-minus-before total is calculated only when every deliverable in both snapshots has an estimate and all units match exactly. Missing estimates, unestimated additions, mixed units, or two empty snapshots produce unknown delta. No conversion or estimation is performed. Removed deliverables subtract their explicit estimate. Unit labels and supplied estimates are not independently verified.

IDs are case-sensitive, 1–80 characters, start with an ASCII letter or digit, and contain only ASCII letters/digits, `.`, `_`, or `-`. Deliverable IDs are unique in each manifest. Acceptance IDs are unique within their parent deliverable. Duplicate JSON object keys and nonstandard NaN/Infinity constants are rejected. Empty deliverable and acceptance lists are permitted; missing acceptance is not.

Order does not affect equality. Text is compared exactly, including whitespace and case. Missing optional text differs from present text. An ID change is a removal and addition. New/removed deliverables include their whole acceptance list in one change; existing deliverables produce individual criterion changes. Changed project metadata is reported separately. No fuzzy similarity, price estimate, risk score, or legal inference is applied.

Evidence uses JSON pointers (zero-based array indices) into each original parsed document and SHA-256 of the original input bytes. Reformatting JSON changes a hash but does not itself change scope. A hash establishes which file was compared; it does not authenticate its author. Reports are deterministic for identical bytes and path arguments.
