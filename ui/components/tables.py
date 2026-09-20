import html
from typing import List, Dict, Any

def render_comparison_table(schemes: List[Dict[str, Any]]) -> str:
    """
    Renders a factual 2-4 scheme side-by-side comparison table.
    Never gives a 'best' verdict; presents raw factual criteria.
    """
    if not schemes:
        return '<p style="font-size: 13px; color: #64748b; padding: 12px;">Select 2 to 4 schemes to view a side-by-side factual comparison table.</p>'

    if len(schemes) < 2:
        return '<p style="font-size: 13px; color: #b45309; padding: 12px; background-color: #fef3c7; border-radius: 8px;">Please select at least 2 schemes to compare.</p>'

    schemes = schemes[:4] # Max 4 schemes

    headers_html = '<th style="padding: 10px; background-color: #f1f5f9; border: 1px solid #cbd5e1; text-align: left; font-size: 12px; font-weight: 700; color: #334155; width: 140px;">Attribute</th>'
    for s in schemes:
        name = html.escape(str(s.get("name", s.get("scheme_name", "Scheme"))))
        headers_html += f'<th style="padding: 10px; background-color: #f8fafc; border: 1px solid #cbd5e1; text-align: left; font-size: 13px; font-weight: 700; color: #0f172a;">{name}</th>'

    rows_data = [
        ("Department", lambda s: html.escape(str(s.get("department", "N/A")))),
        ("State / Scope", lambda s: html.escape(str(s.get("state", "Central / State")))),
        ("Category", lambda s: html.escape(str(s.get("category", "General")))),
        ("Benefits", lambda s: html.escape(str(s.get("benefits", "Not specified")))),
        ("Eligibility Criteria", lambda s: _format_eligibility_criteria(s)),
        ("Application URL", lambda s: f'<a href="{html.escape(s.get("application_url", "#"))}" target="_blank" style="color: #059669; font-weight: 600;">Apply Link</a>' if s.get("application_url") else "N/A")
    ]

    body_html = ""
    for label, extractor in rows_data:
        body_html += f'<tr><td style="padding: 8px 10px; border: 1px solid #e2e8f0; font-weight: 700; font-size: 12px; color: #475569; background-color: #f8fafc;">{label}</td>'
        for s in schemes:
            val = extractor(s)
            body_html += f'<td style="padding: 8px 10px; border: 1px solid #e2e8f0; font-size: 12px; color: #1e293b; vertical-align: top;">{val}</td>'
        body_html += '</tr>'

    return f'''
    <div style="overflow-x: auto; margin-top: 12px;">
        <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; border: 1px solid #cbd5e1;">
            <thead>
                <tr>{headers_html}</tr>
            </thead>
            <tbody>
                {body_html}
            </tbody>
        </table>
    </div>
    '''

def _format_eligibility_criteria(scheme: Dict[str, Any]) -> str:
    rules = scheme.get("eligibility_rules", {})
    if isinstance(rules, dict) and "rules" in rules:
        rule_list = rules["rules"]
        items = []
        for r in rule_list:
            f = html.escape(str(r.get("field", "")).replace("_", " ").title())
            op = html.escape(str(r.get("op", "")))
            v = html.escape(str(r.get("value", "")))
            items.append(f"• <strong>{f}</strong>: {op} {v}")
        return "<br>".join(items) if items else "No structured rules specified"
    elif isinstance(scheme.get("rule_results"), list) and scheme["rule_results"]:
        items = []
        for r in scheme["rule_results"]:
            f = html.escape(str(r.get("field", "")).replace("_", " ").title())
            op = html.escape(str(r.get("op", "")))
            v = html.escape(str(r.get("required_value", "")))
            items.append(f"• <strong>{f}</strong>: {op} {v}")
        return "<br>".join(items)
    return "See official source for criteria"
