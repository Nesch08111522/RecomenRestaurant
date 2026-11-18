"""Resolve repeated IDs in the historical moderation export without editing source files."""
from collections import defaultdict


def reconcile(records, audit_rows):
    groups = defaultdict(list)
    for row in records:
        try:
            identifier = int(row["id"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("La moderación contiene un registro sin identificador entero.") from None
        groups[identifier].append(row)
    references = defaultdict(set)
    for event in audit_rows:
        reference = (event.get("metadata") or {}).get("moderation_id")
        if reference is not None:
            references[int(reference)].add(str(event.get("resource_id")))
    next_id = max(groups, default=0) + 1
    replacements = {}
    for old_id, rows in groups.items():
        if len(rows) == 1:
            continue
        targets = references[old_id]
        matches = [row for row in rows if str(row.get("content_id")) in targets]
        if targets and (len(targets) != 1 or len(matches) != 1):
            raise ValueError(f"La referencia histórica de moderación {old_id} requiere revisión.")
        keep = matches[0] if matches else rows[0]
        for row in rows:
            if row is not keep:
                replacements[id(row)] = dict(row, legacy_id=old_id, id=next_id)
                next_id += 1
    return [replacements.get(id(row), row) for row in records]
