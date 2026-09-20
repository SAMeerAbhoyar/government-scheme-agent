import os
import json
import logging
import gradio as gr

from api_client import APIClient, APIClientError
from components.cards import render_scheme_card, render_status_badge, render_rule_rows
from components.tables import render_comparison_table
from components.admin import (
    render_admin_metrics, render_unverified_queue, render_changes_feed,
    render_source_health, render_feedback_list
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GradioApp")

api_client = APIClient()

MANDATORY_DISCLAIMER_FOOTER = """
<div style="text-align: center; font-size: 11px; color: #64748b; margin-top: 24px; padding: 12px; border-top: 1px solid #e2e8f0;">
    *Your profile appears to match the currently retrieved eligibility information. Final eligibility is determined by the relevant authority.*
</div>
"""

# State helper functions
def handle_login(email, password):
    if not email or not password:
        gr.Warning("Please enter both email and password.")
        return gr.update(), gr.update(), "Please enter both email and password.", gr.update(visible=False)
    try:
        data = api_client.login(email, password)
        token = data.get("access_token")
        if not token:
            return gr.update(), gr.update(), "Login failed: No access token returned.", gr.update(visible=False)

        user = api_client.get_me(token)
        user_name = user.get("name", "User")
        role = user.get("role", "user")
        is_admin = (role == "admin")

        gr.Info(f"Welcome back, {user_name}!")
        status_msg = f"Logged in as {user_name} ({user.get('email')}) — Role: {role.upper()}"
        return token, status_msg, "Login successful!", gr.update(visible=is_admin)

    except APIClientError as e:
        gr.Warning(e.message)
        return gr.update(), gr.update(), f"Login error: {e.message}", gr.update(visible=False)

def handle_signup(name, email, password, consent):
    if not consent:
        gr.Warning("You must agree to the data processing consent to create an account.")
        return "You must agree to data processing consent."
    if not name or not email or not password:
        gr.Warning("Please fill in all required fields.")
        return "Please fill in all required fields."
    try:
        data = api_client.signup(name=name, email=email, password=password, consent=consent)
        gr.Info("Account created successfully! Please log in above.")
        return f"Account created for {data.get('email')}. You can now log in."
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Signup failed: {e.message}"

def handle_logout():
    gr.Info("Logged out successfully.")
    return None, "Not logged in", gr.update(visible=False)

def load_profile_data(token):
    if not token:
        gr.Warning("Please log in to view your profile.")
        return [gr.update() for _ in range(17)] + ["Please log in to view profile."]
    try:
        p = api_client.get_profile(token)
        return [
            p.get("age") or None,
            p.get("gender") or "prefer_not_to_say",
            p.get("state") or "Maharashtra",
            p.get("district") or "",
            p.get("rural_urban") or "prefer_not_to_say",
            p.get("domicile_state") or "Maharashtra",
            p.get("marital_status") or "prefer_not_to_say",
            p.get("education_level") or "",
            p.get("course") or "",
            p.get("year") or "",
            p.get("occupation") or "",
            p.get("employment_status") or "",
            p.get("annual_income") or None,
            p.get("family_size") or None,
            p.get("land_holding_acres") or None,
            p.get("social_category") or "prefer_not_to_say",
            p.get("disability") if p.get("disability") is not None else False,
            p.get("minority") if p.get("minority") is not None else False,
            p.get("bpl_card") if p.get("bpl_card") is not None else False,
            "Profile loaded successfully."
        ]
    except APIClientError as e:
        gr.Warning(e.message)
        return [gr.update() for _ in range(19)] + [f"Error loading profile: {e.message}"]

def save_profile_data(token, age, gender, state, district, rural_urban, domicile_state, marital_status,
                      edu_level, course, year, occupation, emp_status, annual_income, family_size,
                      land_acres, social_cat, disability, minority, bpl_card):
    if not token:
        gr.Warning("Please log in first.")
        return "Please log in first."
    try:
        profile_data = {
            "age": int(age) if age is not None and age != "" else None,
            "gender": None if gender == "prefer_not_to_say" else gender,
            "state": state,
            "district": district if district else None,
            "rural_urban": None if rural_urban == "prefer_not_to_say" else rural_urban,
            "domicile_state": domicile_state if domicile_state else None,
            "marital_status": None if marital_status == "prefer_not_to_say" else marital_status,
            "education_level": edu_level if edu_level else None,
            "course": course if course else None,
            "year": year if year else None,
            "occupation": occupation if occupation else None,
            "employment_status": emp_status if emp_status else None,
            "annual_income": float(annual_income) if annual_income is not None and annual_income != "" else None,
            "family_size": int(family_size) if family_size is not None and family_size != "" else None,
            "land_holding_acres": float(land_acres) if land_acres is not None and land_acres != "" else None,
            "social_category": None if social_cat == "prefer_not_to_say" else social_cat,
            "disability": bool(disability),
            "minority": bool(minority),
            "bpl_card": bool(bpl_card)
        }
        api_client.update_profile(token, profile_data)
        gr.Info("Profile saved successfully!")
        return "Profile saved successfully."
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error saving profile: {e.message}"

def run_mode1_search(token, prompt, category_filter):
    if not token:
        gr.Warning("Please log in first.")
        return '<p style="color: #e11d48; padding: 12px;">Please log in to discover schemes.</p>', []
    if not prompt:
        gr.Warning("Please enter a search prompt.")
        return '<p style="color: #e11d48; padding: 12px;">Please enter a search prompt.</p>', []

    try:
        search_prompt = prompt
        if category_filter and category_filter != "All":
            search_prompt += f" in category {category_filter}"

        res = api_client.discover_query(token, search_prompt)
        matches = res.get("results", [])
        if not matches:
            gr.Info("No matching schemes found for your query.")
            return '<div style="padding: 20px; text-align: center; color: #64748b;">No schemes found matching your search. Try broadening your keywords.</div>', []

        cards_html = "".join([render_scheme_card(m) for m in matches])
        gr.Info(f"Found {len(matches)} matching schemes!")
        return cards_html, matches
    except APIClientError as e:
        gr.Warning(e.message)
        return f'<p style="color: #e11d48; padding: 12px;">Search failed: {e.message}</p>', []

def run_mode2_matching(token):
    if not token:
        gr.Warning("Please log in first.")
        return '<p style="color: #e11d48; padding: 12px;">Please log in to run AI matching.</p>', []

    try:
        res = api_client.discover_profile(token)
        matches = res.get("results", [])
        if not matches:
            gr.Info("No active schemes match your current profile.")
            return '<div style="padding: 20px; text-align: center; color: #64748b;">No active schemes matched your profile criteria. Complete more profile details to unlock more schemes!</div>', []

        cards_html = "".join([render_scheme_card(m) for m in matches])
        gr.Info(f"Profile matching complete: {len(matches)} schemes evaluated!")
        return cards_html, matches
    except APIClientError as e:
        gr.Warning(e.message)
        return f'<p style="color: #e11d48; padding: 12px;">Matching failed: {e.message}</p>', []

def handle_inline_answer(token, field_name, value):
    if not token:
        gr.Warning("Please log in first.")
        return "Please log in first."
    if not field_name or value == "":
        gr.Warning("Please specify both field name and value.")
        return "Field name and value required."

    try:
        # Convert value types if numeric or boolean
        val_converted = value
        if str(value).lower() in ("true", "yes", "1"):
            val_converted = True
        elif str(value).lower() in ("false", "no", "0"):
            val_converted = False
        else:
            try:
                val_converted = float(value)
            except ValueError:
                pass

        api_client.submit_profile_answers(token, {field_name: val_converted})
        gr.Info(f"Updated {field_name}! Re-run discovery to view updated status.")
        return f"Successfully updated {field_name}. Please re-run matching to update scheme card status."
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Failed to submit answer: {e.message}"

def handle_save_scheme(token, scheme_id):
    if not token:
        gr.Warning("Please log in first.")
        return "Please log in first."
    if not scheme_id:
        gr.Warning("Please enter a scheme ID.")
        return "Scheme ID required."
    try:
        api_client.save_scheme(token, scheme_id.strip())
        gr.Info("Scheme saved to your bookmarks!")
        return "Scheme saved successfully!"
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error: {e.message}"

def load_saved_schemes(token):
    if not token:
        return '<p style="color: #64748b; padding: 12px;">Log in to view saved schemes.</p>'
    try:
        saved = api_client.get_saved_schemes(token)
        if not saved:
            return '<div style="padding: 20px; text-align: center; color: #64748b;">No saved schemes bookmarked yet.</div>'

        cards = []
        for item in saved:
            s = item.get("scheme", {})
            if s:
                cards.append(render_scheme_card(s, is_saved=True))
        return "".join(cards) if cards else '<div style="padding: 20px; text-align: center; color: #64748b;">No saved schemes found.</div>'
    except APIClientError as e:
        return f'<p style="color: #e11d48; padding: 12px;">Error: {e.message}</p>'

def load_history(token):
    if not token:
        return '<p style="color: #64748b; padding: 12px;">Log in to view search history.</p>'
    try:
        history = api_client.get_search_history(token)
        if not history:
            return '<div style="padding: 20px; text-align: center; color: #64748b;">No search history recorded yet.</div>'

        rows = []
        for h in history:
            mode = h.get("mode", "manual")
            query = h.get("query", "Profile Discovery")
            created_at = h.get("created_at", "")
            rows.append(f'<div style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 12px;"><strong>[{mode.upper()}]</strong> {query} <span style="color: #94a3b8; font-size: 11px; float: right;">{created_at}</span></div>')
        return "".join(rows)
    except APIClientError as e:
        return f'<p style="color: #e11d48; padding: 12px;">Error: {e.message}</p>'

def generate_comparison(token, schemes_json_raw):
    if not token:
        gr.Warning("Please log in first.")
        return '<p style="color: #e11d48; padding: 12px;">Log in to compare schemes.</p>'
    try:
        if not schemes_json_raw:
            return '<p style="color: #64748b; padding: 12px;">Enter 2 to 4 scheme JSON objects or IDs to generate side-by-side comparison table.</p>'
        parsed = json.loads(schemes_json_raw)
        if not isinstance(parsed, list):
            parsed = [parsed]
        return render_comparison_table(parsed)
    except Exception as e:
        return f'<p style="color: #e11d48; padding: 12px;">Invalid JSON array format: {str(e)}</p>'

def check_notifications_timer(token):
    if not token:
        return "Notifications (0)", '<p style="color: #64748b; padding: 12px;">Log in to view notifications.</p>'
    try:
        res = api_client.get_notifications(token)
        unread_count = res.get("unread_count", 0)
        notifs = res.get("notifications", [])
        tab_label = f"Notifications ({unread_count})" if unread_count > 0 else "Notifications"

        if not notifs:
            return tab_label, '<div style="padding: 20px; text-align: center; color: #64748b;">No notifications.</div>'

        items = []
        for n in notifs:
            msg = n.get("message", "")
            read = n.get("read", False)
            created = n.get("created_at", "")
            bg = "#ffffff" if read else "#eef2ff"
            border = "#e2e8f0" if read else "#c7d2fe"
            items.append(f'''
            <div style="background-color: {bg}; border: 1px solid {border}; border-radius: 8px; padding: 10px; margin-bottom: 8px; font-size: 12px;">
                <p style="margin: 0; font-weight: {'600' if not read else '400'}; color: #1e293b;">{msg}</p>
                <span style="font-size: 10px; color: #94a3b8; margin-top: 4px; display: block;">{created}</span>
            </div>
            ''')
        return tab_label, "".join(items)
    except Exception:
        return "Notifications", '<p style="color: #64748b; padding: 12px;">Unable to load notifications.</p>'

def mark_all_read(token):
    if not token:
        gr.Warning("Please log in first.")
        return "Notifications (0)", '<p style="color: #64748b;">Log in required.</p>'
    try:
        api_client.mark_all_notifications_read(token)
        gr.Info("All notifications marked as read.")
        return check_notifications_timer(token)
    except APIClientError as e:
        gr.Warning(e.message)
        return check_notifications_timer(token)

# Admin Handlers
def load_admin_dashboard(token):
    if not token:
        return "Admin access required.", "", "", "", ""
    try:
        ov = api_client.get_admin_overview(token)
        unv = api_client.get_admin_unverified(token)
        ch = api_client.get_admin_changes(token)
        hl = api_client.get_admin_source_health(token)
        fb = api_client.get_admin_feedback(token)

        return (
            render_admin_metrics(ov),
            render_unverified_queue(unv),
            render_changes_feed(ch),
            render_source_health(hl),
            render_feedback_list(fb)
        )
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error: {e.message}", "", "", "", ""

def handle_admin_verify(token, scheme_id):
    if not token or not scheme_id:
        gr.Warning("Token and Scheme ID required.")
        return "Scheme ID required."
    try:
        res = api_client.verify_admin_scheme(token, scheme_id.strip())
        gr.Info(f"Scheme verified successfully!")
        return res.get("message", "Verified.")
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error: {e.message}"

def handle_admin_reject(token, scheme_id):
    if not token or not scheme_id:
        gr.Warning("Token and Scheme ID required.")
        return "Scheme ID required."
    try:
        res = api_client.reject_admin_scheme(token, scheme_id.strip())
        gr.Info("Scheme rejected.")
        return res.get("message", "Rejected.")
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error: {e.message}"

def handle_admin_ingest_now(token):
    if not token:
        gr.Warning("Log in as Admin first.")
        return "Admin login required."
    try:
        gr.Info("Triggering offline ingestion run...")
        res = api_client.trigger_admin_ingest_now(token)
        gr.Info("Manual ingestion finished!")
        return res.get("message", "Ingestion completed.")
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error: {e.message}"


# Build Gradio Interface
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="blue",
    neutral_hue="slate"
)

with gr.Blocks(theme=theme, title="Government Scheme Recommendation Agent") as demo:
    session_token = gr.State(value=None)
    current_results_state = gr.State(value=[])

    gr.Markdown(
        """
        # 🏛️ Automated Government Scheme Recommendation Agent
        ### Central & Maharashtra Official Scheme Matching Platform
        """
    )

    with gr.Row():
        user_status_label = gr.Markdown("Status: **Not logged in**")
        logout_btn = gr.Button("Sign Out", size="sm", variant="secondary")

    logout_btn.click(fn=handle_logout, outputs=[session_token, user_status_label])

    with gr.Tabs() as main_tabs:

        # TAB 1: AUTHENTICATION
        with gr.Tab("Sign In / Register"):
            gr.Markdown("### Account Authentication")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Sign In")
                    login_email = gr.Textbox(label="Email Address", placeholder="rahul.student@demo.gov.in")
                    login_password = gr.Textbox(label="Password", type="password", placeholder="User@123")
                    login_btn = gr.Button("Sign In", variant="primary")
                    login_status = gr.Markdown()

                with gr.Column():
                    gr.Markdown("#### Register New Account")
                    signup_name = gr.Textbox(label="Full Name", placeholder="Rahul Sharma")
                    signup_email = gr.Textbox(label="Email Address", placeholder="rahul@example.com")
                    signup_password = gr.Textbox(label="Password", type="password")
                    signup_consent = gr.Checkbox(
                        label="I consent to secure processing of my profile data for government scheme matching",
                        value=True
                    )
                    gr.Markdown(
                        "*Privacy Notice: Sensitive attributes (income, caste category, disability status) are encrypted at rest with Fernet AES and never shared with third parties.*",
                        elem_classes=["text-xs", "text-slate-500"]
                    )
                    signup_btn = gr.Button("Create Account", variant="secondary")
                    signup_status = gr.Markdown()

        # TAB 2: PROFILE MANAGEMENT
        with gr.Tab("Profile Management"):
            gr.Markdown("### Citizen Profile Details")
            load_prof_btn = gr.Button("🔄 Load Current Profile", size="sm")
            prof_status = gr.Markdown()

            with gr.Accordion("1. Personal Details", open=True):
                prof_age = gr.Number(label="Age (Years)", precision=0)
                prof_gender = gr.Dropdown(label="Gender", choices=["male", "female", "transgender", "prefer_not_to_say"], value="prefer_not_to_say")
                prof_state = gr.Textbox(label="Current State", value="Maharashtra")
                prof_district = gr.Textbox(label="District", placeholder="Pune / Nashik / Nagpur")
                prof_rural_urban = gr.Dropdown(label="Area Type", choices=["rural", "urban", "prefer_not_to_say"], value="prefer_not_to_say")
                prof_domicile = gr.Textbox(label="Domicile State", value="Maharashtra")
                prof_marital = gr.Dropdown(label="Marital Status", choices=["single", "married", "widowed", "prefer_not_to_say"], value="prefer_not_to_say")

            with gr.Accordion("2. Education", open=False):
                prof_edu = gr.Textbox(label="Education Level", placeholder="Undergraduate / Postgraduate / Class 10 / Class 12")
                prof_course = gr.Textbox(label="Course Name", placeholder="B.Tech Engineering / MBBS / B.Com")
                prof_year = gr.Textbox(label="Academic Year", placeholder="1st Year / 2nd Year")

            with gr.Accordion("3. Employment & Occupation", open=False):
                prof_occ = gr.Textbox(label="Primary Occupation", placeholder="Student / Farmer / Self-Employed / Unemployed")
                prof_emp_status = gr.Textbox(label="Employment Status", placeholder="Employed / Unemployed / Student")

            with gr.Accordion("4. Financial Details", open=False):
                prof_income = gr.Number(label="Annual Family Income (INR ₹)", precision=2)
                prof_family = gr.Number(label="Family Size", precision=0)
                prof_land = gr.Number(label="Land Holding (Acres)", precision=2)
                prof_bpl = gr.Checkbox(label="BPL Card Holder (Below Poverty Line)")

            with gr.Accordion("5. Social Category & Special Status (Encrypted at Rest)", open=False):
                prof_cat = gr.Dropdown(label="Social Category", choices=["SC", "ST", "OBC", "EWS", "General", "prefer_not_to_say"], value="prefer_not_to_say")
                prof_disability = gr.Checkbox(label="Person with Disability (PwD)")
                prof_minority = gr.Checkbox(label="Minority Community Member")

            save_prof_btn = gr.Button("💾 Save Profile", variant="primary")

        # TAB 3: SCHEME DISCOVERY & MATCHING
        with gr.Tab("Discover Schemes"):
            gr.Markdown("### Scheme Discovery & Eligibility Matching")

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### Mode 1: Search Specific Need")
                    mode1_cat = gr.Dropdown(label="Category Filter", choices=["All", "Education", "Agriculture", "Housing", "Social Welfare"], value="All")
                    mode1_prompt = gr.Textbox(label="Search Prompt", placeholder="e.g. scholarship for engineering student in maharashtra")
                    mode1_btn = gr.Button("🔍 Search Schemes", variant="primary")

                with gr.Column(scale=1):
                    gr.Markdown("#### Mode 2: AI Profile Matching")
                    gr.Markdown("Runs deterministic eligibility matching engine across all active Central & Maharashtra schemes for your saved profile.")
                    mode2_btn = gr.Button("🤖 Let AI Find Matching Schemes", variant="primary")

            gr.Markdown("---")
            gr.Markdown("### Evaluation Results")
            results_cards_output = gr.HTML(value='<div style="padding: 20px; text-align: center; color: #94a3b8;">Run a search prompt or click "Let AI Find Matching Schemes" to view evaluation results.</div>')

            with gr.Accordion("Quick Actions & Missing Info Answers", open=False):
                with gr.Row():
                    ans_field = gr.Textbox(label="Missing Field Name", placeholder="e.g. annual_income")
                    ans_val = gr.Textbox(label="Field Value", placeholder="e.g. 150000")
                    ans_btn = gr.Button("Submit Answer", size="sm")
                ans_status = gr.Markdown()

                with gr.Row():
                    save_id_input = gr.Textbox(label="Scheme ID to Bookmark", placeholder="Enter scheme ID")
                    save_id_btn = gr.Button("Save Scheme", size="sm")
                save_status = gr.Markdown()

        # TAB 4: SAVED SCHEMES
        with gr.Tab("Saved Bookmarks"):
            gr.Markdown("### Your Bookmarked Schemes")
            load_saved_btn = gr.Button("🔄 Refresh Saved Schemes", size="sm")
            saved_output = gr.HTML()

        # TAB 5: SEARCH HISTORY
        with gr.Tab("Search History"):
            gr.Markdown("### Search & Discovery History")
            load_history_btn = gr.Button("🔄 Refresh History", size="sm")
            history_output = gr.HTML()

        # TAB 6: COMPARE SCHEMES
        with gr.Tab("Compare Schemes"):
            gr.Markdown("### Factual 2-4 Scheme Comparison")
            gr.Markdown("Paste JSON list of schemes or IDs to generate a side-by-side factual comparison table. *Note: Provides raw factual criteria only; never gives a subjective 'best' verdict.*")
            comp_input = gr.Code(label="Schemes Data (JSON Array)", language="json", value='[\n  {\n    "name": "Scheme A",\n    "department": "Higher Education",\n    "state": "Maharashtra",\n    "category": "Education",\n    "benefits": "50% Fee Reimbursement"\n  },\n  {\n    "name": "Scheme B",\n    "department": "Social Welfare",\n    "state": "Central",\n    "category": "Education",\n    "benefits": "100% Scholarship"\n  }\n]')
            comp_btn = gr.Button("Generate Comparison Table", variant="primary")
            comp_output = gr.HTML()

        # TAB 7: NOTIFICATIONS
        with gr.Tab("Notifications") as notif_tab:
            gr.Markdown("### Citizen Notifications & Alerts")
            with gr.Row():
                mark_all_btn = gr.Button("Check & Mark All as Read", size="sm")
            notif_output = gr.HTML()

        # TAB 8: ADMIN DASHBOARD (ROLE-GATED)
        with gr.Tab("Admin Command Center", visible=False) as admin_tab:
            gr.Markdown("### 🛡️ Admin Verification & Source Health")
            load_admin_btn = gr.Button("🔄 Refresh Admin Dashboard", variant="primary")
            
            admin_metrics_out = gr.HTML()

            with gr.Accordion("1. Unverified Scheme Queue (Side-by-Side Verification)", open=True):
                admin_unverified_out = gr.HTML()
                with gr.Row():
                    admin_scheme_id = gr.Textbox(label="Scheme ID", placeholder="Enter ID to verify or reject")
                    admin_verify_btn = gr.Button("✓ Verify Scheme", size="sm", variant="primary")
                    admin_reject_btn = gr.Button("✗ Reject Scheme", size="sm")
                admin_action_status = gr.Markdown()

            with gr.Accordion("2. Scheme Version Changes Feed", open=False):
                admin_changes_out = gr.HTML()

            with gr.Accordion("3. Source Health & Crawl Metrics", open=False):
                admin_health_out = gr.HTML()

            with gr.Accordion("4. Citizen Feedback Log", open=False):
                admin_feedback_out = gr.HTML()

            with gr.Accordion("5. Manual Ingestion Trigger", open=False):
                admin_ingest_btn = gr.Button("▶ Run Offline Ingestion Now", variant="stop")
                admin_ingest_status = gr.Markdown()

    # Disclaimer Footer
    gr.HTML(MANDATORY_DISCLAIMER_FOOTER)

    # Polling Timer for Notifications (every 10s)
    timer = gr.Timer(value=10.0, active=True)
    timer.tick(
        fn=check_notifications_timer,
        inputs=[session_token],
        outputs=[notif_tab, notif_output]
    )

    # Event Wiring
    login_btn.click(
        fn=handle_login,
        inputs=[login_email, login_password],
        outputs=[session_token, user_status_label, login_status, admin_tab]
    )

    signup_btn.click(
        fn=handle_signup,
        inputs=[signup_name, signup_email, signup_password, signup_consent],
        outputs=[signup_status]
    )

    load_prof_btn.click(
        fn=load_profile_data,
        inputs=[session_token],
        outputs=[
            prof_age, prof_gender, prof_state, prof_district, prof_rural_urban,
            prof_domicile, prof_marital, prof_edu, prof_course, prof_year,
            prof_occ, prof_emp_status, prof_income, prof_family, prof_land,
            prof_cat, prof_disability, prof_minority, prof_bpl, prof_status
        ]
    )

    save_prof_btn.click(
        fn=save_profile_data,
        inputs=[
            session_token, prof_age, prof_gender, prof_state, prof_district,
            prof_rural_urban, prof_domicile, prof_marital, prof_edu, prof_course,
            prof_year, prof_occ, prof_emp_status, prof_income, prof_family,
            prof_land, prof_cat, prof_disability, prof_minority, prof_bpl
        ],
        outputs=[prof_status]
    )

    mode1_btn.click(
        fn=run_mode1_search,
        inputs=[session_token, mode1_prompt, mode1_cat],
        outputs=[results_cards_output, current_results_state]
    )

    mode2_btn.click(
        fn=run_mode2_matching,
        inputs=[session_token],
        outputs=[results_cards_output, current_results_state]
    )

    ans_btn.click(
        fn=handle_inline_answer,
        inputs=[session_token, ans_field, ans_val],
        outputs=[ans_status]
    )

    save_id_btn.click(
        fn=handle_save_scheme,
        inputs=[session_token, save_id_input],
        outputs=[save_status]
    )

    load_saved_btn.click(
        fn=load_saved_schemes,
        inputs=[session_token],
        outputs=[saved_output]
    )

    load_history_btn.click(
        fn=load_history,
        inputs=[session_token],
        outputs=[history_output]
    )

    comp_btn.click(
        fn=generate_comparison,
        inputs=[session_token, comp_input],
        outputs=[comp_output]
    )

    mark_all_btn.click(
        fn=mark_all_read,
        inputs=[session_token],
        outputs=[notif_tab, notif_output]
    )

    load_admin_btn.click(
        fn=load_admin_dashboard,
        inputs=[session_token],
        outputs=[
            admin_metrics_out, admin_unverified_out, admin_changes_out,
            admin_health_out, admin_feedback_out
        ]
    )

    admin_verify_btn.click(
        fn=handle_admin_verify,
        inputs=[session_token, admin_scheme_id],
        outputs=[admin_action_status]
    )

    admin_reject_btn.click(
        fn=handle_admin_reject,
        inputs=[session_token, admin_scheme_id],
        outputs=[admin_action_status]
    )

    admin_ingest_btn.click(
        fn=handle_admin_ingest_now,
        inputs=[session_token],
        outputs=[admin_ingest_status]
    )

if __name__ == "__main__":
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    logger.info(f"Starting Gradio UI on {server_name}:{server_port}...")
    demo.launch(server_name=server_name, server_port=server_port, share=False)
