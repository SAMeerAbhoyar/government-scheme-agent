import pytest
from app.eligibility import (
    RuleLeaf, RuleGroup, OperatorEnum, EvaluationStatus, evaluate_eligibility
)

def test_single_leaf_evaluation_match():
    rule = RuleLeaf(field="age", op=OperatorEnum.GTE, value=18)
    profile = {"age": 20}
    res = evaluate_eligibility(RuleGroup(all_of=[rule]), profile)
    assert res.overall_status == EvaluationStatus.MATCH

def test_single_leaf_evaluation_nomatch():
    rule = RuleLeaf(field="annual_income", op=OperatorEnum.LTE, value=250000)
    profile = {"annual_income": 500000}
    res = evaluate_eligibility(RuleGroup(all_of=[rule]), profile)
    assert res.overall_status == EvaluationStatus.NO_MATCH

def test_single_leaf_missing_data_unknown():
    rule = RuleLeaf(field="annual_income", op=OperatorEnum.LTE, value=250000)
    profile = {"annual_income": None}
    res = evaluate_eligibility(RuleGroup(all_of=[rule]), profile)
    assert res.overall_status == EvaluationStatus.UNKNOWN

def test_all_of_group_tri_state():
    rule1 = RuleLeaf(field="state", op=OperatorEnum.EQ, value="Maharashtra")
    rule2 = RuleLeaf(field="social_category", op=OperatorEnum.IN, value=["SC", "ST", "OBC"])
    rule3 = RuleLeaf(field="age", op=OperatorEnum.BETWEEN, value=[18, 35])

    group = RuleGroup(all_of=[rule1, rule2, rule3])

    # 1. All match
    prof_match = {"state": "Maharashtra", "social_category": "OBC", "age": 25}
    assert evaluate_eligibility(group, prof_match).overall_status == EvaluationStatus.MATCH

    # 2. One no_match (state is Delhi)
    prof_nomatch = {"state": "Delhi", "social_category": "OBC", "age": 25}
    assert evaluate_eligibility(group, prof_nomatch).overall_status == EvaluationStatus.NO_MATCH

    # 3. Missing age (none no_match, but age is missing -> UNKNOWN)
    prof_unknown = {"state": "Maharashtra", "social_category": "OBC", "age": None}
    assert evaluate_eligibility(group, prof_unknown).overall_status == EvaluationStatus.UNKNOWN

def test_any_of_group_tri_state():
    rule1 = RuleLeaf(field="disability", op=OperatorEnum.EQ, value=True)
    rule2 = RuleLeaf(field="bpl_card", op=OperatorEnum.EQ, value=True)

    group = RuleGroup(any_of=[rule1, rule2])

    # 1. One match (has bpl_card)
    prof_match = {"disability": False, "bpl_card": True}
    assert evaluate_eligibility(group, prof_match).overall_status == EvaluationStatus.MATCH

    # 2. All no_match
    prof_nomatch = {"disability": False, "bpl_card": False}
    assert evaluate_eligibility(group, prof_nomatch).overall_status == EvaluationStatus.NO_MATCH

    # 3. One unknown, other no_match -> UNKNOWN
    prof_unknown = {"disability": None, "bpl_card": False}
    assert evaluate_eligibility(group, prof_unknown).overall_status == EvaluationStatus.UNKNOWN

def test_nested_complex_rules():
    # Eligible if (State == Maharashtra AND (social_category IN [SC, ST] OR annual_income <= 100000))
    state_rule = RuleLeaf(field="state", op=OperatorEnum.EQ, value="Maharashtra")
    category_rule = RuleLeaf(field="social_category", op=OperatorEnum.IN, value=["SC", "ST"])
    income_rule = RuleLeaf(field="annual_income", op=OperatorEnum.LTE, value=100000)

    sub_or = RuleGroup(any_of=[category_rule, income_rule])
    root_and = RuleGroup(all_of=[state_rule, sub_or])

    # Case A: Maharashtra General with 80k income -> MATCH via income
    prof_a = {"state": "Maharashtra", "social_category": "General", "annual_income": 80000}
    assert evaluate_eligibility(root_and, prof_a).overall_status == EvaluationStatus.MATCH

    # Case B: Maharashtra ST with unknown income -> MATCH via ST
    prof_b = {"state": "Maharashtra", "social_category": "ST", "annual_income": None}
    assert evaluate_eligibility(root_and, prof_b).overall_status == EvaluationStatus.MATCH

    # Case C: Maharashtra General with unknown income -> UNKNOWN
    prof_c = {"state": "Maharashtra", "social_category": "General", "annual_income": None}
    assert evaluate_eligibility(root_and, prof_c).overall_status == EvaluationStatus.UNKNOWN

    # Case D: Gujarat ST with 80k income -> NO_MATCH (fails state rule)
    prof_d = {"state": "Gujarat", "social_category": "ST", "annual_income": 80000}
    assert evaluate_eligibility(root_and, prof_d).overall_status == EvaluationStatus.NO_MATCH
