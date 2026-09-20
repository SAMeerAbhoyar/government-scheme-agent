import logging
from typing import Dict, Any, Tuple, List, Union
from app.eligibility.schema import (
    RuleLeaf, RuleGroup, OperatorEnum, EvaluationStatus,
    LeafEvaluationDetail, SchemeEvaluationResult
)

logger = logging.getLogger(__name__)

def _normalize_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, str):
        return val.strip()
    return val

def _to_float(val: Any) -> Tuple[bool, float]:
    try:
        if isinstance(val, (int, float)):
            return True, float(val)
        if isinstance(val, str):
            cleaned = val.replace(",", "").strip()
            return True, float(cleaned)
    except (ValueError, TypeError):
        pass
    return False, 0.0

def evaluate_leaf(leaf: RuleLeaf, profile_data: Dict[str, Any]) -> LeafEvaluationDetail:
    try:
        field_name = str(leaf.field) if leaf.field is not None else "unknown"
        actual_val = profile_data.get(field_name) if profile_data else None
        actual_val = _normalize_value(actual_val)
        expected_val = _normalize_value(leaf.value)

        if actual_val is None:
            return LeafEvaluationDetail(
                field=field_name,
                op=leaf.op.value if hasattr(leaf.op, "value") else str(leaf.op),
                expected_value=leaf.value,
                actual_value=None,
                status=EvaluationStatus.UNKNOWN,
                source_quote=leaf.source_quote
            )

        op = leaf.op
        status = EvaluationStatus.NO_MATCH

        if op == OperatorEnum.EQ:
            if leaf.field == "state" and isinstance(expected_val, str) and expected_val.lower() in ("central", "all india", "india"):
                status = EvaluationStatus.MATCH
            elif isinstance(actual_val, str) and isinstance(expected_val, str):
                status = EvaluationStatus.MATCH if actual_val.lower() == expected_val.lower() else EvaluationStatus.NO_MATCH
            else:
                status = EvaluationStatus.MATCH if actual_val == expected_val else EvaluationStatus.NO_MATCH

        elif op == OperatorEnum.NEQ:
            if isinstance(actual_val, str) and isinstance(expected_val, str):
                status = EvaluationStatus.MATCH if actual_val.lower() != expected_val.lower() else EvaluationStatus.NO_MATCH
            else:
                status = EvaluationStatus.MATCH if actual_val != expected_val else EvaluationStatus.NO_MATCH

        elif op in (OperatorEnum.LT, OperatorEnum.LTE, OperatorEnum.GT, OperatorEnum.GTE):
            actual_ok, actual_num = _to_float(actual_val)
            exp_ok, exp_num = _to_float(expected_val)

            if not (actual_ok and exp_ok):
                status = EvaluationStatus.UNKNOWN
            else:
                if op == OperatorEnum.LT:
                    status = EvaluationStatus.MATCH if actual_num < exp_num else EvaluationStatus.NO_MATCH
                elif op == OperatorEnum.LTE:
                    status = EvaluationStatus.MATCH if actual_num <= exp_num else EvaluationStatus.NO_MATCH
                elif op == OperatorEnum.GT:
                    status = EvaluationStatus.MATCH if actual_num > exp_num else EvaluationStatus.NO_MATCH
                elif op == OperatorEnum.GTE:
                    status = EvaluationStatus.MATCH if actual_num >= exp_num else EvaluationStatus.NO_MATCH

        elif op == OperatorEnum.IN:
            if isinstance(expected_val, (list, tuple, set)):
                target_set = {str(item).strip().lower() for item in expected_val}
                val_str = str(actual_val).strip().lower()
                status = EvaluationStatus.MATCH if val_str in target_set else EvaluationStatus.NO_MATCH
            else:
                status = EvaluationStatus.UNKNOWN

        elif op == OperatorEnum.NOT_IN:
            if isinstance(expected_val, (list, tuple, set)):
                target_set = {str(item).strip().lower() for item in expected_val}
                val_str = str(actual_val).strip().lower()
                status = EvaluationStatus.MATCH if val_str not in target_set else EvaluationStatus.NO_MATCH
            else:
                status = EvaluationStatus.UNKNOWN

        elif op == OperatorEnum.BETWEEN:
            if isinstance(expected_val, (list, tuple)) and len(expected_val) == 2:
                act_ok, act_num = _to_float(actual_val)
                min_ok, min_num = _to_float(expected_val[0])
                max_ok, max_num = _to_float(expected_val[1])
                if act_ok and min_ok and max_ok:
                    status = EvaluationStatus.MATCH if min_num <= act_num <= max_num else EvaluationStatus.NO_MATCH
                else:
                    status = EvaluationStatus.UNKNOWN
            else:
                status = EvaluationStatus.UNKNOWN

        return LeafEvaluationDetail(
            field=field_name,
            op=leaf.op.value if hasattr(leaf.op, "value") else str(leaf.op),
            expected_value=leaf.value,
            actual_value=actual_val,
            status=status,
            source_quote=leaf.source_quote
        )
    except Exception as e:
        logger.warning(f"Error evaluating leaf node: {e}")
        return LeafEvaluationDetail(
            field=str(getattr(leaf, "field", "unknown")),
            op=str(getattr(leaf.op, "value", leaf.op)) if hasattr(leaf, "op") else "==",
            expected_value=getattr(leaf, "value", None),
            actual_value=None,
            status=EvaluationStatus.UNKNOWN,
            source_quote=getattr(leaf, "source_quote", None)
        )

def evaluate_node(
    node: Union[RuleLeaf, RuleGroup, Dict[str, Any]],
    profile_data: Dict[str, Any]
) -> Tuple[EvaluationStatus, List[LeafEvaluationDetail]]:
    try:
        if isinstance(node, dict):
            if "field" in node and "op" in node:
                node = RuleLeaf(**node)
            else:
                node = RuleGroup(**node)

        if isinstance(node, RuleLeaf):
            detail = evaluate_leaf(node, profile_data)
            return detail.status, [detail]

        if isinstance(node, RuleGroup):
            details: List[LeafEvaluationDetail] = []

            if node.all_of is not None:
                statuses = []
                for child in node.all_of:
                    child_status, child_details = evaluate_node(child, profile_data)
                    statuses.append(child_status)
                    details.extend(child_details)

                if EvaluationStatus.NO_MATCH in statuses:
                    return EvaluationStatus.NO_MATCH, details
                if EvaluationStatus.UNKNOWN in statuses:
                    return EvaluationStatus.UNKNOWN, details
                return EvaluationStatus.MATCH, details

            if node.any_of is not None:
                statuses = []
                for child in node.any_of:
                    child_status, child_details = evaluate_node(child, profile_data)
                    statuses.append(child_status)
                    details.extend(child_details)

                if EvaluationStatus.MATCH in statuses:
                    return EvaluationStatus.MATCH, details
                if EvaluationStatus.UNKNOWN in statuses:
                    return EvaluationStatus.UNKNOWN, details
                return EvaluationStatus.NO_MATCH, details

            if node.not_of is not None:
                child_status, child_details = evaluate_node(node.not_of, profile_data)
                details.extend(child_details)
                if child_status == EvaluationStatus.MATCH:
                    return EvaluationStatus.NO_MATCH, details
                if child_status == EvaluationStatus.NO_MATCH:
                    return EvaluationStatus.MATCH, details
                return EvaluationStatus.UNKNOWN, details

        return EvaluationStatus.UNKNOWN, []
    except Exception as e:
        logger.warning(f"Error evaluating rule node: {e}")
        return EvaluationStatus.UNKNOWN, []

def evaluate_eligibility(
    rule_tree: Union[RuleGroup, Dict[str, Any]],
    profile_data: Dict[str, Any]
) -> SchemeEvaluationResult:
    try:
        overall_status, details = evaluate_node(rule_tree, profile_data)

        if overall_status == EvaluationStatus.MATCH:
            reason = "Citizen matches all criteria for this scheme."
        elif overall_status == EvaluationStatus.NO_MATCH:
            unmatched = [d.field for d in details if d.status == EvaluationStatus.NO_MATCH]
            reason = f"Citizen does not meet criteria for fields: {', '.join(unmatched)}."
        else:
            unknowns = [d.field for d in details if d.status == EvaluationStatus.UNKNOWN]
            reason = f"Missing profile information for fields: {', '.join(unknowns)}."

        return SchemeEvaluationResult(
            overall_status=overall_status,
            summary_reason=reason,
            details=details
        )
    except Exception as e:
        logger.warning(f"Error in evaluate_eligibility: {e}")
        return SchemeEvaluationResult(
            overall_status=EvaluationStatus.UNKNOWN,
            summary_reason="Could not evaluate this scheme.",
            details=[]
        )
