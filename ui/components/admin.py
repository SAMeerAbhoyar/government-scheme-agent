import html
import json
from typing import List, Dict, Any

def render_admin_metrics(overview: Dict[str, Any]) -> str:
    if not overview:
        return '<p style="font-size: 13px; color: #64748b;">No metrics available.</p>'

    by_status = overview.get("schemes_by_status", {})
    by_cat = overview.get("schemes_by_category", {})
    last_run = overview.get("last_run")

    active_cnt = by_status.get("active", 0)
    unverified_cnt = overview.get("unverified_count", by_status.get("unverified", 0))
    expired_cnt = by_status.get("expired", 0) + by_status.get("outdated", 0)
    last_fetched = last_run.get("fetched", 0) if last_run else 0

    return f'''
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px;">
        <div style="background-color: #ffffff; padding: 14px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Active Schemes</div>
            <div style="font-size: 24px; font-weight: 800; color: #0f172a; margin-top: 4px;">{active_cnt}</div>
        </div>
        <div style="background-color: #ffffff; padding: 14px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <div style="font-size: 11px; font-weight: 700; color: #d97706; text-transform: uppercase;">Unverified Queue</div>
            <div style="font-size: 24px; font-weight: 800; color: #d97706; margin-top: 4px;">{unverified_cnt}</div>
        </div>
        <div style="background-color: #ffffff; padding: 14px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Expired / Outdated</div>
            <div style="font-size: 24px; font-weight: 800; color: #64748b; margin-top: 4px;">{expired_cnt}</div>
        </div>
        <div style="background-color: #ffffff; padding: 14px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <div style="font-size: 11px; font-weight: 700; color: #4f46e5; text-transform: uppercase;">Last Run Fetched</div>
            <div style="font-size: 24px; font-weight: 800; color: #4f46e5; margin-top: 4px;">{last_fetched}</div>
        </div>
    </div>
    '''

def render_unverified_queue(unverified_schemes: List[Dict[str, Any]]) -> str:
    if not unverified_schemes:
        return '<div style="background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; color: #64748b; font-size: 13px;">🎉 No unverified schemes in the queue. All extractions verified!</div>'

    items_html = []
    for s in unverified_schemes:
        sid = html.escape(str(s.get("id", "")))
        name = html.escape(str(s.get("name", "Scheme")))
        dept = html.escape(str(s.get("department", "Department")))
        state = html.escape(str(s.get("state", "State")))
        cat = html.escape(str(s.get("category", "General")))
        conf = s.get("extraction_confidence", 0.0)
        source_url = html.escape(str(s.get("source_url", "")))
        quotes = s.get("source_quotes", [])
        rules = s.get("eligibility_rules", {})
        rules_json = html.escape(json.dumps(rules, indent=2))

        quotes_html = f'<p style="margin: 2px 0;"><a href="{source_url}" target="_blank" style="color: #4f46e5;">{source_url}</a></p>'
        if quotes:
            for q in quotes:
                quotes_html += f'<div style="font-size: 11px; color: #475569; font-style: italic; background: #f1f5f9; padding: 4px 8px; border-left: 3px solid #cbd5e1; margin-top: 4px;">"{html.escape(str(q))}"</div>'

        items_html.append(f'''
        <div style="background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h4 style="margin: 0 0 2px 0; font-size: 15px; font-weight: 700; color: #0f172a;">{name}</h4>
                    <span style="font-size: 11px; color: #64748b;">{dept} • {state} • {cat} | Confidence: {conf}</span>
                </div>
                <div style="font-size: 11px; font-weight: 700; color: #d97706; background: #fef3c7; padding: 2px 8px; border-radius: 9999px;">ID: {sid[:8]}</div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px; font-size: 12px;">
                <div style="background-color: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <strong style="color: #334155; font-size: 11px; text-transform: uppercase;">Source Quotes / Links:</strong>
                    {quotes_html}
                </div>
                <div style="background-color: #0f172a; color: #f1f5f9; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 11px; overflow-x: auto; max-height: 140px;">
                    <strong style="color: #38bdf8; font-size: 10px; text-transform: uppercase; display: block; margin-bottom: 4px;">Extracted Rules JSON:</strong>
                    <pre style="margin: 0;">{rules_json}</pre>
                </div>
            </div>
        </div>
        ''')

    return "".join(items_html)

def render_changes_feed(changes: List[Dict[str, Any]]) -> str:
    if not changes:
        return '<p style="font-size: 13px; color: #64748b;">No version changes recorded yet.</p>'

    items = []
    for c in changes:
        sname = html.escape(str(c.get("scheme_name", "Scheme")))
        dt = html.escape(str(c.get("detected_at", "")))
        diff = html.escape(json.dumps(c.get("diff", {}), indent=2))
        items.append(f'''
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin-bottom: 8px; font-size: 12px;">
            <div style="display: flex; justify-content: space-between; font-weight: 700; color: #0f172a;">
                <span>{sname}</span>
                <span style="color: #64748b; font-size: 11px;">{dt}</span>
            </div>
            <pre style="background: #0f172a; color: #34d399; padding: 8px; border-radius: 6px; font-size: 11px; margin-top: 6px; overflow-x: auto;">{diff}</pre>
        </div>
        ''')
    return "".join(items)

def render_source_health(health_list: List[Dict[str, Any]]) -> str:
    if not health_list:
        return '<p style="font-size: 13px; color: #64748b;">No source records tracked.</p>'

    rows = []
    for h in health_list:
        sname = html.escape(str(h.get("scheme_name", "")))
        url = html.escape(str(h.get("source_url", "")))
        fails = h.get("consecutive_fetch_failures", 0)
        status = html.escape(str(h.get("status", "active")))
        fail_color = "#f43f5e" if fails > 0 else "#10b981"

        rows.append(f'''
        <tr style="border-bottom: 1px solid #f1f5f9; font-size: 12px;">
            <td style="padding: 8px; font-weight: 600;">{sname}</td>
            <td style="padding: 8px; color: #64748b; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{url}</td>
            <td style="padding: 8px; font-weight: 700; color: {fail_color}; text-align: center;">{fails}</td>
            <td style="padding: 8px; text-align: center;"><span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 9999px; background: #ecfdf5; color: #047857;">{status}</span></td>
        </tr>
        ''')

    return f'''
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;">
            <thead>
                <tr style="background: #f8fafc; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase;">
                    <th style="padding: 8px; text-align: left;">Scheme</th>
                    <th style="padding: 8px; text-align: left;">Source URL</th>
                    <th style="padding: 8px; text-align: center;">Failures</th>
                    <th style="padding: 8px; text-align: center;">Status</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>
    '''

def render_feedback_list(feedback_list: List[Dict[str, Any]]) -> str:
    if not feedback_list:
        return '<p style="font-size: 13px; color: #64748b;">No feedback entries recorded yet.</p>'

    items = []
    for f in feedback_list:
        email = html.escape(str(f.get("user_email", "")))
        comment = html.escape(str(f.get("comment", "No comment")))
        useful = f.get("useful", True)
        badge = '<span style="background: #d1fae5; color: #047857; font-weight: 700; padding: 2px 6px; border-radius: 4px; font-size: 11px;">👍 Useful</span>' if useful else '<span style="background: #ffe4e6; color: #be123c; font-weight: 700; padding: 2px 6px; border-radius: 4px; font-size: 11px;">👎 Not Useful</span>'

        items.append(f'''
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin-bottom: 8px; font-size: 12px; display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <strong style="color: #0f172a;">{email}</strong>
                <p style="margin: 4px 0 0 0; color: #475569;">"{comment}"</p>
            </div>
            <div>{badge}</div>
        </div>
        ''')

    return "".join(items)
