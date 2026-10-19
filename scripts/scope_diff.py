#!/usr/bin/env python3
"""Compare explicitly structured scope manifests. Python standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def check_keys(obj, required, optional, where):
    if not isinstance(obj, dict):
        raise ValueError(f"{where}: expected object")
    if set(obj) - required - optional or required - set(obj):
        raise ValueError(f"{where}: required keys {sorted(required)}; optional {sorted(optional)}")


def check_text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: expected nonempty string")


def indexed(items, where, criterion=False):
    if not isinstance(items, list):
        raise ValueError(f"{where}: expected array")
    found = {}
    required = {"id", "text"} if criterion else {"id", "title", "acceptance"}
    optional = set() if criterion else {"owner", "due", "description", "dependencies", "estimate"}
    for pos, item in enumerate(items):
        loc = f"{where}/{pos}"
        check_keys(item, required, optional, loc)
        key = item["id"]
        if not isinstance(key, str) or not ID.fullmatch(key):
            raise ValueError(f"{loc}/id: expected stable ID (letters, digits, dot, underscore, hyphen)")
        if key in found:
            raise ValueError(f"{loc}/id: duplicate ID {key}")
        for field in required | optional:
            if field in item and field not in {"acceptance", "dependencies", "estimate"}:
                check_text(item[field], f"{loc}/{field}")
        if not criterion:
            indexed(item["acceptance"], loc + "/acceptance", True)
            deps = item.get("dependencies", [])
            if not isinstance(deps, list) or any(not isinstance(d, str) or not ID.fullmatch(d) for d in deps) or len(deps) != len(set(deps)):
                raise ValueError(f"{loc}/dependencies: expected unique stable IDs")
            if "estimate" in item:
                est = item["estimate"]
                check_keys(est, {"value", "unit"}, set(), loc + "/estimate")
                if type(est["value"]) is not int or est["value"] < 0:
                    raise ValueError(f"{loc}/estimate/value: expected nonnegative integer")
                check_text(est["unit"], loc + "/estimate/unit")
        found[key] = (pos, item)
    return found


def validate(data):
    check_keys(data, {"schema_version", "deliverables"}, {"project"}, "manifest")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version: expected integer 1")
    if "project" in data:
        check_text(data["project"], "project")
    indexed(data["deliverables"], "/deliverables")
    return data


def load(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant {value}")))
    return validate(data), hashlib.sha256(raw).hexdigest()


def compare(before, after):
    validate(before)
    validate(after)
    changes = []

    def change(kind, key, old, new, old_pointer, new_pointer, field=None):
        entry = dict(kind=kind, id=key, before=old, after=new,
                     before_pointer=old_pointer, after_pointer=new_pointer)
        if field:
            entry["field"] = field
        changes.append(entry)

    if before.get("project") != after.get("project"):
        change("project_changed", "project", before.get("project"), after.get("project"),
               "/project" if "project" in before else None, "/project" if "project" in after else None)
    old_map = indexed(before["deliverables"], "/deliverables")
    new_map = indexed(after["deliverables"], "/deliverables")
    for key in sorted(old_map.keys() | new_map.keys()):
        oi, old = old_map.get(key, (None, None))
        ni, new = new_map.get(key, (None, None))
        op = f"/deliverables/{oi}" if old is not None else None
        np = f"/deliverables/{ni}" if new is not None else None
        if old is None or new is None:
            change("deliverable_added" if old is None else "deliverable_removed", key, old, new, op, np)
            continue
        for field in ("title", "description", "owner", "due", "estimate"):
            if old.get(field) != new.get(field):
                change("deliverable_changed", key, old.get(field), new.get(field),
                       op + "/" + field if field in old else None,
                       np + "/" + field if field in new else None, field)
        if set(old.get("dependencies", [])) != set(new.get("dependencies", [])):
            change("dependencies_changed", key, sorted(old.get("dependencies", [])), sorted(new.get("dependencies", [])),
                   op + "/dependencies" if "dependencies" in old else None,
                   np + "/dependencies" if "dependencies" in new else None)
        oc = indexed(old["acceptance"], op + "/acceptance", True)
        nc = indexed(new["acceptance"], np + "/acceptance", True)
        for cid in sorted(oc.keys() | nc.keys()):
            ci, c_old = oc.get(cid, (None, None))
            cj, c_new = nc.get(cid, (None, None))
            if c_old == c_new:
                continue
            kind = "acceptance_added" if c_old is None else "acceptance_removed" if c_new is None else "acceptance_changed"
            change(kind, key, c_old, c_new,
                   f"{op}/acceptance/{ci}" if c_old is not None else None,
                   f"{np}/acceptance/{cj}" if c_new is not None else None, cid)
    dangling = []
    for side, mapping in (("before", old_map), ("after", new_map)):
        for key, (pos, item) in sorted(mapping.items()):
            for i, dep in enumerate(item.get("dependencies", [])):
                if dep not in mapping:
                    dangling.append({"side": side, "id": key, "target": dep, "pointer": f"/deliverables/{pos}/dependencies/{i}"})
    estimates = [d.get("estimate") for d in before["deliverables"] + after["deliverables"]]
    units = {e["unit"] for e in estimates if e is not None}
    delta = {"status": "unknown", "reason": "missing estimates or mixed units"}
    if estimates and all(e is not None for e in estimates) and len(units) == 1:
        delta = {"status": "known", "unit": next(iter(units)), "value": sum(d["estimate"]["value"] for d in after["deliverables"]) - sum(d["estimate"]["value"] for d in before["deliverables"])}
    return {"schema_version": 1, "status": "changed" if changes else "unchanged", "change_count": len(changes), "changes": changes, "dangling_dependencies": dangling, "estimate_delta": delta}


def fenced_json(value):
    """Keep untrusted text inert, even if it contains fences or HTML."""
    payload = json.dumps(value, indent=2, ensure_ascii=True)
    for character, escaped in (("`", "\\u0060"), ("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        payload = payload.replace(character, escaped)
    return "```json\n" + payload + "\n```"


def render(report):
    lines = [f"# Scope Diff: {report['status']} ({report['change_count']} changes)"]
    if "sources" in report:
        lines.extend(["", "## Sources", "", fenced_json(report["sources"])])
    for change in report["changes"]:
        lines.extend(["", "## Change", "", fenced_json(change)])
    if report["dangling_dependencies"]:
        lines.extend(["", "## Dangling dependencies", "", fenced_json(report["dangling_dependencies"])])
    lines.extend(["", "## Estimate delta", "", fenced_json(report["estimate_delta"]), "", "Changes require human review; this report does not establish effort, consent, or legal effect."])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--format", choices=("text", "markdown", "json"), default="markdown")
    parser.add_argument("--fail-on-change", action="store_true", help="explicitly request default exit 1 on findings")
    parser.add_argument("--exit-zero", action="store_true", help="exit 0 on valid input even when findings exist")
    parser.add_argument("--output", help="create a new report file; refuse to overwrite an existing path")
    args = parser.parse_args(argv)
    try:
        before, bh = load(args.before)
        after, ah = load(args.after)
        report = compare(before, after)
        report["sources"] = {"before": {"path": str(args.before), "sha256": bh}, "after": {"path": str(args.after), "sha256": ah}}
        output = json.dumps(report, indent=2, ensure_ascii=True) + "\n" if args.format == "json" else render(report)
        if args.output:
            with open(args.output, "x", encoding="utf-8") as handle:
                handle.write(output)
        else:
            print(output, end="")
        return 1 if not args.exit_zero and (report["changes"] or report["dangling_dependencies"]) else 0
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(f"scope-diff: invalid input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
