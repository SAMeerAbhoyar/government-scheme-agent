import html
from typing import Dict, Any, List, Optional

def render_status_badge(status: str, unverified: bool = False) -> str:
    status_lower = (status or "").lower()
    badge_html = ""

    if status_lower in ("potentially_relevant", "match"):
        badge_html = '<span style="background-color: #d1fae5; color: #065f46; font-weight: 700; font-size: 11px; padding: 3px 10px; border-radius: 9999px; border: 1px solid #a7f3d0; display: inline-flex; align-items: center; gap: 4px;">✓ Potentially Relevant</span>'
    elif status_lower in ("cannot_determine", "partial"):
        badge_html = '<span style="background-color: #fef3c7; color: #92400e; font-weight: 700; font-size: 11px; padding: 3px 10px; border-radius: 9999px; border: 1px solid #fde68a; display: inline-flex; align-items: center; gap: 4px;">? Cannot Determine (Missing Info)</span>'
    else:
        badge_html = '<span style="background-color: #ffe4e6; color: #9f1239; font-weight: 700; font-size: 11px; padding: 3px 10px; border-radius: 9999px; border: 1px solid #fecdd3; display: inline-flex; align-items: center; gap: 4px;">✗ Not Currently Matching</span>'

    if unverified:
        badge_html += ' <span style="background-color: #fff7ed; color: #c2410c; font-weight: 600; font-size: 10px; padding: 2px 8px; border-radius: 9999px; border: 1px solid #ffedd5;">⚠️ Unverified</span>'

    return badge_html

def render_rule_rows(rule_results: List[Dict[str, Any]]) -> str:
    if not rule_results:
        return '<p style="font-size: 12px; color: #64748b; margin: 4px 0;">No structured eligibility rules evaluated.</p>'

    rows = []
    for r in rule_results:
        res = str(r.get("result", "")).lower()
        field = html.escape(str(r.get("field", "")).replace("_", " ").title())
        op = html.escape(str(r.get("op", "")))
        req_val = html.escape(str(r.get("required_value", "")))
        user_val = html.escape(str(r.get("user_value", "Not provided")))
        quote = r.get("source_quote")

        if res == "match":
            icon = '<span style="color: #10b981; font-weight: 800; font-size: 14px;">✓</span>'
            status_txt = f'<span style="color: #065f46;">Matches requirement ({op} {req_val})</span>'
        elif res == "no_match":
            icon = '<span style="color: #f43f5e; font-weight: 800; font-size: 14px;">✗</span>'
            status_txt = f'<span style="color: #9f1239;">Requires {op} {req_val} (Your profile: {user_val})</span>'
        else:
            icon = '<span style="color: #f59e0b; font-weight: 800; font-size: 14px;">?</span>'
            status_txt = f'<span style="color: #92400e;">Missing profile data (Requires {op} {req_val})</span>'

        quote_html = ""
        if quote:
            quote_html = f'<div style="font-size: 11px; color: #64748b; font-style: italic; margin-top: 2px; border-left: 2px solid #cbd5e1; padding-left: 6px;">"{html.escape(str(quote))}"</div>'

        rows.append(f'''
        <div style="display: flex; items-center; gap: 8px; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed #e2e8f0;">
            <div style="width: 20px; text-align: center;">{icon}</div>
            <div style="flex: 1;">
                <strong>{field}</strong>: {status_txt}
                {quote_html}
            </div>
        </div>
        ''')

    return "".join(rows)

def render_scheme_card(match: Dict[str, Any], is_saved: bool = False) -> str:
    scheme_id = match.get("scheme_id", match.get("id", ""))
    title = html.escape(str(match.get("scheme_name", match.get("name", "Government Scheme"))))
    dept = html.escape(str(match.get("department", "Government Portal")))
    state = html.escape(str(match.get("state", "Central / State")))
    cat = html.escape(str(match.get("category", "General")))
    status = match.get("status", "potentially_relevant")
    unverified = match.get("unverified", False)
    explanation = match.get("explanation", match.get("reason", ""))
    source_url = match.get("source_url")
    app_url = match.get("application_url")
    rule_results = match.get("rule_results", [])

    badge = render_status_badge(status, unverified)
    rules_html = render_rule_rows(rule_results)

    links_html = ""
    if source_url:
        links_html += f'<a href="{html.escape(source_url)}" target="_blank" style="color: #4f46e5; text-decoration: none; font-weight: 600; font-size: 12px; margin-right: 12px;">🔗 Official Source</a>'
    if app_url:
        links_html += f'<a href="{html.escape(app_url)}" target="_blank" style="color: #059669; text-decoration: none; font-weight: 600; font-size: 12px;">📝 Apply Online</a>'

    explanation_html = ""
    if explanation:
        safe_exp = html.escape(str(explanation)).replace("\n", "<br>")
        explanation_title = "Why am I seeing this?" if status == "potentially_relevant" else "Why don't I match?"
        explanation_html = f'''
        <details style="margin-top: 10px; background-color: #f8fafc; border-radius: 8px; padding: 8px 12px; border: 1px solid #e2e8f0;">
            <summary style="font-weight: 700; font-size: 12px; color: #334155; cursor: pointer;">💡 {explanation_title}</summary>
            <div style="font-size: 12px; color: #475569; margin-top: 6px; line-height: 1.5;">{safe_exp}</div>
        </details>
        '''

    return f'''
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 8px;">
            <div>
                <h3 style="margin: 0 0 4px 0; font-size: 16px; font-weight: 700; color: #0f172a;">{title}</h3>
                <span style="font-size: 11px; color: #64748b; font-weight: 500;">{dept} • {state} • {cat}</span>
            </div>
            <div>{badge}</div>
        </div>

        <div style="margin: 10px 0;">
            {rules_html}
        </div>

        {explanation_html}

        <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center;">
            <div>{links_html}</div>
            <div style="font-size: 11px; color: #94a3b8;">ID: {scheme_id[:8]}...</div>
        </div>
    </div>
    '''
