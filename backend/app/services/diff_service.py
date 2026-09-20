from typing import Dict, Any, List

def extract_rules_flat_map(rules: Any) -> Dict[str, Any]:
    """Helper to extract flat map of field -> value/op from RuleGroup or Dict."""
    flat = {}
    if not rules:
        return flat

    def traverse(node: Any):
        if isinstance(node, dict):
            if "field" in node:
                flat[node["field"]] = {
                    "op": node.get("op"),
                    "value": node.get("value"),
                    "source_quote": node.get("source_quote")
                }
            if "all_of" in node and node["all_of"]:
                for child in node["all_of"]:
                    traverse(child)
            if "any_of" in node and node["any_of"]:
                for child in node["any_of"]:
                    traverse(child)
        elif hasattr(node, "all_of"):
            if node.all_of:
                for child in node.all_of:
                    traverse(child)

    traverse(rules)
    return flat

def compute_scheme_diff(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a granular field-level diff between two scheme extraction payloads.
    Compares eligibility rules, benefits, required documents, and deadline dates.
    """
    changed_fields = []
    details = {}

    # 1. Compare top-level string/numeric fields
    for field in ["name", "benefits", "application_process", "deadline_date", "department", "category", "state"]:
        old_val = old_data.get(field)
        new_val = new_data.get(field)

        # Normalize None vs empty string
        old_str = str(old_val).strip() if old_val is not None else ""
        new_str = str(new_val).strip() if new_val is not None else ""

        if old_str != new_str:
            changed_fields.append(field)
            details[field] = {"old": old_val, "new": new_val}

    # 2. Compare documents list
    old_docs = set(old_data.get("documents") or [])
    new_docs = set(new_data.get("documents") or [])
    if old_docs != new_docs:
        changed_fields.append("documents")
        details["documents"] = {
            "added": sorted(list(new_docs - old_docs)),
            "removed": sorted(list(old_docs - new_docs))
        }

    # 3. Compare eligibility rules AST
    old_rules_flat = extract_rules_flat_map(old_data.get("eligibility_rules"))
    new_rules_flat = extract_rules_flat_map(new_data.get("eligibility_rules"))

    all_rule_fields = set(old_rules_flat.keys()) | set(new_rules_flat.keys())
    rule_diffs = {}

    for rf in all_rule_fields:
        r_old = old_rules_flat.get(rf)
        r_new = new_rules_flat.get(rf)

        if r_old != r_new:
            rule_diffs[rf] = {"old": r_old, "new": r_new}

    if rule_diffs:
        changed_fields.append("eligibility_rules")
        details["eligibility_rules"] = rule_diffs

    has_changes = len(changed_fields) > 0

    return {
        "has_changes": has_changes,
        "changed_fields": changed_fields,
        "details": details
    }
