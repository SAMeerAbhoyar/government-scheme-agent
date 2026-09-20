import os
import sys
import json
import logging
import gradio as gr

# Ensure backend and ui folders are in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, ".."))
backend_dir = os.path.join(repo_root, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

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
<div style="text-align: center; font-size: 12px; color: #64748b; margin-top: 24px; padding: 16px; border-top: 1px solid #e2e8f0;">
    Results are indicative only. Final eligibility is decided by the official authority. Always confirm on the official portal.
</div>
"""

DEMO_CREDENTIALS = {
    "Student": ("rahul.student@demo.gov.in", "User@123"),
    "Farmer": ("ramesh.farmer@demo.gov.in", "User@123"),
    "Woman": ("anita.women@demo.gov.in", "User@123"),
    "Senior": ("eknath.senior@demo.gov.in", "User@123"),
}

# Login handler
def handle_login(email, password):
    if not email or not password:
        gr.Warning("Please enter your email and password.")
        return (
            gr.update(), "", "Please enter your email and password.",
            gr.update(visible=True), gr.update(visible=False),
            gr.update(visible=False), gr.update()
        )
    try:
        data = api_client.login(email, password)
        token = data.get("access_token")
        if not token:
            return (
                gr.update(), "", "Unable to sign in. Please check your details.",
                gr.update(visible=True), gr.update(visible=False),
                gr.update(visible=False), gr.update()
            )

        user = api_client.get_me(token)
        user_name = user.get("name", "User")
        role = user.get("role", "user")
        is_admin = (role == "admin")

        gr.Info(f"Welcome, {user_name}!")
        user_info_html = f"<div style='text-align: right; font-size: 13px; color: #334155;'>Signed in as <strong>{user_name}</strong> <span style='background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; margin-left: 6px;'>{role.upper()}</span></div>"

        return (
            token,
            user_info_html,
            "Signed in successfully.",
            gr.update(visible=False),    # hide login_view
            gr.update(visible=True),     # show app_view
            gr.update(visible=is_admin), # tab_admin visibility
            gr.update(selected="tab_discover") # switch to Discover tab
        )

    except APIClientError as e:
        gr.Warning(e.message)
        return (
            gr.update(), "", f"Sign in failed: {e.message}",
            gr.update(visible=True), gr.update(visible=False),
            gr.update(visible=False), gr.update()
        )

def handle_demo_login(role_name):
    if role_name not in DEMO_CREDENTIALS:
        return handle_login("", "")
    email, password = DEMO_CREDENTIALS[role_name]
    return handle_login(email, password)

def handle_signup(name, email, password, consent):
    if not consent:
        gr.Warning("Please check the consent box to create an account.")
        return "Please agree to data consent to proceed."
    if not name or not email or not password:
        gr.Warning("Please fill in all registration fields.")
        return "All fields are required."
    try:
        data = api_client.signup(name=name, email=email, password=password, consent=consent)
        gr.Info("Account created! You can now sign in.")
        return f"Account created for {data.get('email')}. Please sign in."
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Registration failed: {e.message}"

def handle_logout():
    gr.Info("Signed out.")
    return (
        None,
        "",
        gr.update(visible=True),   # show login_view
        gr.update(visible=False),  # hide app_view
        gr.update(visible=False)   # hide tab_admin
    )

def load_profile_data(token):
    if not token:
        return [gr.update() for _ in range(19)] + ["Please sign in to view your profile."]
    try:
        p = api_client.get_profile(token)
        age_val = p.get("age")
        if age_val is None or age_val == 0 or str(age_val).strip() == "":
            age_val = None
        else:
            try:
                age_val = int(age_val)
                if age_val <= 0:
                    age_val = None
            except (ValueError, TypeError):
                age_val = None

        return [
            age_val,
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
            p.get("annual_income") if p.get("annual_income") is not None else None,
            p.get("family_size") if p.get("family_size") is not None else None,
            p.get("land_holding_acres") if p.get("land_holding_acres") is not None else None,
            p.get("social_category") or "prefer_not_to_say",
            p.get("disability") if p.get("disability") is not None else False,
            p.get("minority") if p.get("minority") is not None else False,
            p.get("bpl_card") if p.get("bpl_card") is not None else False,
            "Profile refreshed."
        ]
    except APIClientError as e:
        return [gr.update() for _ in range(19)] + [f"Could not load profile: {e.message}"]

def save_profile_data(token, age, gender, state, district, rural_urban, domicile_state, marital_status,
                      edu_level, course, year, occupation, emp_status, annual_income, family_size,
                      land_acres, social_cat, disability, minority, bpl_card):
    if not token:
        gr.Warning("Please sign in first.")
        return "Please sign in first."
    try:
        parsed_age = None
        if age is not None and str(age).strip() != "" and age != 0:
            try:
                v = int(age)
                if v > 0:
                    parsed_age = v
            except (ValueError, TypeError):
                parsed_age = None

        profile_data = {
            "age": parsed_age,
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
            "annual_income": float(annual_income) if annual_income is not None and str(annual_income).strip() != "" else None,
            "family_size": int(family_size) if family_size is not None and str(family_size).strip() != "" else None,
            "land_holding_acres": float(land_acres) if land_acres is not None and str(land_acres).strip() != "" else None,
            "social_category": None if social_cat == "prefer_not_to_say" else social_cat,
            "disability": bool(disability),
            "minority": bool(minority),
            "bpl_card": bool(bpl_card)
        }
        api_client.update_profile(token, profile_data)
        gr.Info("Profile saved successfully!")
        return "Profile saved."
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Could not save profile: {e.message}"

def run_mode1_search(token, prompt, category_filter):
    if not token:
        gr.Warning("Please sign in first.")
        return '<p style="color: #64748b; padding: 12px;">Please sign in to search schemes.</p>', []

    try:
        cat_display = category_filter if category_filter and category_filter not in ("All", "All categories") else "All categories"
        effective_cat = category_filter if category_filter and category_filter not in ("All", "All categories") else None
        query_val = str(prompt).strip() if prompt and str(prompt).strip() else None

        res = api_client.discover_query(token, query=query_val, category_filter=effective_cat)
        matches = res.get("matches", []) or res.get("results", [])
        if not matches:
            empty_html = f'''
            <div style="padding: 24px; text-align: center; color: #64748b; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0;">
                <h4 style="margin: 0 0 8px 0; color: #334155; font-size: 16px; font-weight: 700;">No schemes found in {cat_display}</h4>
                <p style="margin: 0; font-size: 14px;">Try selecting a different category or refining your search prompt.</p>
            </div>
            '''
            return empty_html, []

        cards = [render_scheme_card(m) for m in matches]
        count_header = f'<div style="margin-bottom: 16px; font-weight: 700; font-size: 15px; color: #1e293b;">{len(matches)} scheme{"s" if len(matches) != 1 else ""} found in {cat_display}</div>'
        return count_header + "".join(cards), matches
    except APIClientError as e:
        gr.Warning(e.message)
        return f'<p style="color: #e11d48; padding: 12px;">Search request failed: {e.message}</p>', []

def run_mode2_matching(token):
    if not token:
        gr.Warning("Please sign in first.")
        return '<p style="color: #64748b; padding: 12px;">Please sign in to view recommendations.</p>', []

    try:
        res = api_client.discover_profile(token)
        matches = res.get("matches", [])
        if not matches:
            return '<div style="padding: 24px; text-align: center; color: #64748b; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0;">No schemes found for your profile. Try adding more details in My profile.</div>', []

        cards = [render_scheme_card(m) for m in matches]
        count_header = f'<div style="margin-bottom: 16px; font-weight: 700; font-size: 15px; color: #1e293b;">{len(matches)} scheme{"s" if len(matches) != 1 else ""} evaluated for your profile</div>'
        return count_header + "".join(cards), matches
    except APIClientError as e:
        gr.Warning(e.message)
        return f'<p style="color: #e11d48; padding: 12px;">Profile matching failed: {e.message}</p>', []

def handle_inline_answer(token, field_name, value):
    if not token or not field_name or value is None:
        gr.Warning("Field name and value are required.")
        return "Please enter field name and value."
    try:
        parsed_val = value
        val_str = str(value).strip()
        if val_str.lower() in ("true", "yes"):
            parsed_val = True
        elif val_str.lower() in ("false", "no"):
            parsed_val = False
        else:
            try:
                parsed_val = float(val_str) if "." in val_str else int(val_str)
            except ValueError:
                parsed_val = val_str

        api_client.answer_missing_info(token, field_name.strip(), parsed_val)
        gr.Info(f"Updated '{field_name}'. Re-run matching to update results.")
        return f"Updated field '{field_name}'."
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error: {e.message}"

def handle_save_scheme(token, scheme_id):
    if not token or not scheme_id:
        gr.Warning("Scheme ID required.")
        return "Scheme ID required."
    try:
        api_client.save_scheme(token, scheme_id.strip())
        gr.Info("Scheme bookmarked!")
        return "Scheme saved to bookmarks."
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error: {e.message}"

def load_saved_schemes(token):
    if not token:
        return '<p style="color: #64748b; padding: 12px;">Sign in to view saved schemes.</p>'
    try:
        saved = api_client.get_saved_schemes(token)
        if not saved:
            return '<div style="padding: 24px; text-align: center; color: #64748b; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0;">No saved schemes bookmarked yet.</div>'
        cards = [render_scheme_card(s, is_saved=True) for s in saved]
        return "".join(cards)
    except APIClientError as e:
        return f'<p style="color: #e11d48; padding: 12px;">Unable to load saved schemes: {e.message}</p>'

def load_history(token):
    if not token:
        return '<p style="color: #64748b; padding: 12px;">Sign in to view search history.</p>'
    try:
        history = api_client.get_search_history(token)
        if not history:
            return '<div style="padding: 24px; text-align: center; color: #64748b; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0;">No search history available yet.</div>'

        rows = []
        for h in history:
            mode = h.get("mode", "manual")
            query = h.get("query", "Profile Discovery")
            created_at = h.get("created_at", "")
            rows.append(f'<div style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0; font-size: 13px; background: #ffffff;"><strong>[{mode.upper()}]</strong> {query} <span style="color: #94a3b8; font-size: 11px; float: right;">{created_at}</span></div>')
        return "".join(rows)
    except APIClientError as e:
        return f'<p style="color: #e11d48; padding: 12px;">Unable to load history: {e.message}</p>'

def generate_comparison(token, schemes_json_raw):
    if not token:
        gr.Warning("Please sign in first.")
        return '<p style="color: #64748b; padding: 12px;">Sign in to compare schemes.</p>'
    try:
        if not schemes_json_raw:
            return '<p style="color: #64748b; padding: 12px;">Paste 2 to 4 scheme JSON objects to generate comparison table.</p>'
        parsed = json.loads(schemes_json_raw)
        if not isinstance(parsed, list):
            parsed = [parsed]
        return render_comparison_table(parsed)
    except Exception as e:
        return f'<p style="color: #e11d48; padding: 12px;">Invalid JSON format: {str(e)}</p>'

def check_notifications_timer(token):
    if not token:
        return '<p style="color: #64748b; padding: 12px;">Sign in to view notifications.</p>'
    try:
        res = api_client.get_notifications(token)
        notifs = res.get("notifications", [])

        if not notifs:
            return '<div style="padding: 24px; text-align: center; color: #64748b; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0;">No notifications yet.</div>'

        items = []
        for n in notifs:
            msg = n.get("message", "")
            read = n.get("read", False)
            created = n.get("created_at", "")
            bg = "#ffffff" if read else "#eef2ff"
            border = "#e2e8f0" if read else "#c7d2fe"
            items.append(f'''
            <div style="background-color: {bg}; border: 1px solid {border}; border-radius: 8px; padding: 12px; margin-bottom: 8px; font-size: 13px;">
                <p style="margin: 0; font-weight: {'600' if not read else '400'}; color: #1e293b;">{msg}</p>
                <span style="font-size: 11px; color: #94a3b8; margin-top: 4px; display: block;">{created}</span>
            </div>
            ''')
        return "".join(items)
    except Exception:
        return '<p style="color: #64748b; padding: 12px;">Unable to load notifications.</p>'

def mark_all_read(token):
    if not token:
        gr.Warning("Please sign in first.")
        return '<p style="color: #64748b;">Sign in required.</p>'
    try:
        api_client.mark_all_notifications_read(token)
        gr.Info("Notifications marked as read.")
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
        gr.Info("Scheme verified!")
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
        gr.Warning("Admin sign in required.")
        return "Admin sign in required."
    try:
        gr.Info("Triggering offline ingestion run...")
        res = api_client.trigger_admin_ingest_now(token)
        gr.Info("Ingestion completed!")
        return res.get("message", "Ingestion completed.")
    except APIClientError as e:
        gr.Warning(e.message)
        return f"Error: {e.message}"


# Gradio Theme & Custom CSS for Gradio 6 launch()
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="blue",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "sans-serif"]
)

custom_css = """
.gradio-container {
    max-width: 1100px !important;
    margin: 0 auto !important;
    font-size: 15px !important;
}

#login_card {
    max-width: 480px !important;
    margin: 30px auto !important;
    padding: 24px !important;
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
}

.header-bar {
    padding: 12px 16px !important;
    margin-bottom: 16px !important;
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    align-items: center !important;
}
"""

with gr.Blocks(title="Government Scheme Finder") as demo:
    session_token = gr.State(value=None)
    current_results_state = gr.State(value=[])

    # VIEW 1: LOGIN VIEW (Visible by default before sign in)
    with gr.Column(visible=True, elem_id="login_card") as login_view:
        gr.Markdown(
            """
            <div style="text-align: center; margin-bottom: 16px;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #0f172a;">🏛️ Government Scheme Finder</h1>
                <p style="margin: 6px 0 0 0; font-size: 14px; color: #64748b;">Find government schemes you qualify for in Central & Maharashtra</p>
            </div>
            """
        )

        with gr.Tabs():
            with gr.Tab("Sign in"):
                login_email = gr.Textbox(label="Email address", placeholder="e.g. rahul.student@demo.gov.in")
                login_password = gr.Textbox(label="Password", type="password")
                login_btn = gr.Button("Sign in", variant="primary")
                login_status = gr.Markdown()

            with gr.Tab("Create account"):
                signup_name = gr.Textbox(label="Full name", placeholder="Your full name")
                signup_email = gr.Textbox(label="Email address", placeholder="name@example.com")
                signup_password = gr.Textbox(label="Password", type="password")
                signup_consent = gr.Checkbox(
                    label="I consent to processing my profile details for scheme eligibility matching",
                    value=True
                )
                gr.Markdown(
                    "*Sensitive details (income, category, disability) are encrypted in our database. "
                    "To write explanations, some profile-based results may be processed by an external AI service (Google Gemini). "
                    "This is a demo - use fictional details if you prefer.*"
                )
                signup_btn = gr.Button("Create account", variant="secondary")
                signup_status = gr.Markdown()

        # Try a demo profile section
        gr.Markdown(
            """
            <div style="margin-top: 20px; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 16px;">
                <span style="font-size: 13px; font-weight: 600; color: #475569;">Try a demo profile</span>
            </div>
            """
        )
        with gr.Row():
            demo_student_btn = gr.Button("Student", size="sm", variant="secondary")
            demo_farmer_btn = gr.Button("Farmer", size="sm", variant="secondary")
            demo_woman_btn = gr.Button("Woman", size="sm", variant="secondary")
            demo_senior_btn = gr.Button("Senior", size="sm", variant="secondary")

    # VIEW 2: APP VIEW (Hidden before sign in)
    with gr.Column(visible=False, elem_id="app_view") as app_view:
        # Slim Header Bar
        with gr.Row(elem_classes=["header-bar"]):
            with gr.Column(scale=4):
                gr.Markdown("<h2 style='margin: 0; font-size: 18px; font-weight: 800; color: #0f172a;'>🏛️ Government Scheme Finder</h2>")
            with gr.Column(scale=3, min_width=240):
                user_info_label = gr.Markdown("<div style='text-align: right; font-size: 13px; color: #334155;'>Signed in</div>")
            with gr.Column(scale=1, min_width=100):
                logout_btn = gr.Button("Sign out", size="sm", variant="secondary")

        # Tabs in exact order: Discover, My profile, Saved, History, Compare, Notifications, Admin
        with gr.Tabs() as main_tabs:
            with gr.Tab("Discover", id="tab_discover") as tab_discover:
                gr.Markdown("### Discover schemes")

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### I know what I need")
                        mode1_cat = gr.Dropdown(
                            label="Category",
                            choices=[
                                "All categories",
                                "Agriculture",
                                "Girl child",
                                "Women",
                                "Scholarship and education",
                                "Old age",
                                "Poor and BPL support",
                                "Health",
                                "Housing",
                                "Employment"
                            ],
                            value="All categories",
                            info="Select a specific scheme category"
                        )
                        mode1_prompt = gr.Textbox(
                            label="Search prompt",
                            placeholder="e.g. scholarship for engineering student in maharashtra",
                            info="Describe what kind of support you need"
                        )
                        mode1_btn = gr.Button("Search", variant="primary")

                    with gr.Column(scale=1):
                        gr.Markdown("#### Find schemes for me")
                        gr.Markdown("Runs automatic eligibility check against all Central and Maharashtra schemes using your profile.")
                        mode2_btn = gr.Button("Find schemes for my profile", variant="primary", size="lg")

                gr.Markdown("---")
                gr.Markdown("### Evaluation results")
                results_cards_output = gr.HTML(
                    value='<div style="padding: 24px; text-align: center; color: #64748b; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0;">'
                          'Enter a search prompt or click "Find schemes for my profile" to view recommendations.'
                          '</div>'
                )

                with gr.Accordion("Quick actions & answer missing info", open=False):
                    with gr.Row():
                        ans_field = gr.Textbox(label="Missing field name", placeholder="e.g. annual_income")
                        ans_val = gr.Textbox(label="Field value", placeholder="e.g. 150000")
                        ans_btn = gr.Button("Submit answer", size="sm")
                    ans_status = gr.Markdown()

                    with gr.Row():
                        save_id_input = gr.Textbox(label="Scheme ID", placeholder="Enter scheme ID to bookmark")
                        save_id_btn = gr.Button("Save scheme", size="sm")
                    save_status = gr.Markdown()

            with gr.Tab("My profile", id="tab_profile") as tab_profile:
                gr.Markdown("### My profile details")
                with gr.Row():
                    load_prof_btn = gr.Button("Refresh profile", size="sm")
                    save_prof_btn = gr.Button("Save profile", variant="primary", size="sm")
                prof_status = gr.Markdown()

                with gr.Accordion("Personal", open=True):
                    prof_age = gr.Number(label="Your age", precision=0, value=None, info="Leave blank if you prefer not to state")
                    prof_gender = gr.Dropdown(label="Gender", choices=["male", "female", "transgender", "prefer_not_to_say"], value="prefer_not_to_say")
                    prof_state = gr.Textbox(label="Current state", value="Maharashtra")
                    prof_district = gr.Textbox(label="District", placeholder="e.g. Pune, Nashik, Nagpur")
                    prof_rural_urban = gr.Dropdown(label="Area type", choices=["rural", "urban", "prefer_not_to_say"], value="prefer_not_to_say")
                    prof_domicile = gr.Textbox(label="Domicile state", value="Maharashtra")
                    prof_marital = gr.Dropdown(label="Marital status", choices=["single", "married", "widowed", "prefer_not_to_say"], value="prefer_not_to_say")

                with gr.Accordion("Education and work", open=False):
                    prof_edu = gr.Textbox(label="Education level", placeholder="e.g. Undergraduate, Class 10, Class 12")
                    prof_course = gr.Textbox(label="Course name", placeholder="e.g. B.Tech Engineering, B.Com, MBBS")
                    prof_year = gr.Textbox(label="Academic year", placeholder="e.g. 1st Year, 2nd Year")
                    prof_occ = gr.Textbox(label="Primary occupation", placeholder="e.g. Student, Farmer, Self-Employed, Unemployed")
                    prof_emp_status = gr.Textbox(label="Employment status", placeholder="e.g. Employed, Unemployed, Student")

                with gr.Accordion("Money and family", open=False):
                    prof_income = gr.Number(label="Annual family income (₹)", precision=2, info="Income in INR per year")
                    prof_family = gr.Number(label="Family size", precision=0)
                    prof_land = gr.Number(label="Land holding (acres)", precision=2)
                    prof_bpl = gr.Checkbox(label="BPL card holder (Below Poverty Line)")

                with gr.Accordion("Other details", open=False):
                    prof_cat = gr.Dropdown(label="Social category", choices=["SC", "ST", "OBC", "EWS", "General", "prefer_not_to_say"], value="prefer_not_to_say")
                    prof_disability = gr.Checkbox(label="Person with disability (PwD)")
                    prof_minority = gr.Checkbox(label="Minority community member")

            with gr.Tab("Saved", id="tab_saved") as tab_saved:
                gr.Markdown("### Saved schemes")
                load_saved_btn = gr.Button("Refresh saved schemes", size="sm")
                saved_output = gr.HTML()

            with gr.Tab("History", id="tab_history") as tab_history:
                gr.Markdown("### Search history")
                load_history_btn = gr.Button("Refresh history", size="sm")
                history_output = gr.HTML()

            with gr.Tab("Compare", id="tab_compare") as tab_compare:
                gr.Markdown("### Compare schemes")
                gr.Markdown("Paste JSON list of schemes or IDs to generate a side-by-side comparison table.")
                comp_input = gr.Code(label="Schemes data (JSON array)", language="json", value='[\n  {\n    "name": "Scheme A",\n    "department": "Higher Education",\n    "state": "Maharashtra",\n    "category": "Education",\n    "benefits": "50% Fee Reimbursement"\n  },\n  {\n    "name": "Scheme B",\n    "department": "Social Welfare",\n    "state": "Central",\n    "category": "Education",\n    "benefits": "100% Scholarship"\n  }\n]')
                comp_btn = gr.Button("Compare schemes", variant="primary")
                comp_output = gr.HTML()

            with gr.Tab("Notifications", id="tab_notif") as tab_notif:
                gr.Markdown("### Notifications")
                mark_all_btn = gr.Button("Mark all as read", size="sm")
                notif_output = gr.HTML()

            with gr.Tab("Admin", visible=False, id="tab_admin") as tab_admin:
                gr.Markdown("### Admin command center")
                load_admin_btn = gr.Button("Refresh dashboard", variant="primary")
                admin_metrics_out = gr.HTML()

                with gr.Accordion("Unverified scheme queue", open=True):
                    admin_unverified_out = gr.HTML()
                    with gr.Row():
                        admin_scheme_id = gr.Textbox(label="Scheme ID", placeholder="Enter ID")
                        admin_verify_btn = gr.Button("Verify scheme", size="sm", variant="primary")
                        admin_reject_btn = gr.Button("Reject scheme", size="sm")
                    admin_action_status = gr.Markdown()

                with gr.Accordion("Scheme version changes", open=False):
                    admin_changes_out = gr.HTML()

                with gr.Accordion("Source health & crawl metrics", open=False):
                    admin_health_out = gr.HTML()

                with gr.Accordion("Citizen feedback log", open=False):
                    admin_feedback_out = gr.HTML()

                with gr.Accordion("Manual ingestion trigger", open=False):
                    admin_ingest_btn = gr.Button("Run offline ingestion now", variant="stop")
                    admin_ingest_status = gr.Markdown()

    # Footer on every screen
    gr.HTML(MANDATORY_DISCLAIMER_FOOTER)

    # Polling Timer for Notifications (every 10s)
    timer = gr.Timer(value=10.0, active=True)
    timer.tick(
        fn=check_notifications_timer,
        inputs=[session_token],
        outputs=[notif_output]
    )

    # Event Wiring
    login_event = login_btn.click(
        fn=handle_login,
        inputs=[login_email, login_password],
        outputs=[
            session_token, user_info_label, login_status,
            login_view, app_view, tab_admin, main_tabs
        ]
    )
    # Auto load profile on successful login
    login_event.then(
        fn=load_profile_data,
        inputs=[session_token],
        outputs=[
            prof_age, prof_gender, prof_state, prof_district, prof_rural_urban,
            prof_domicile, prof_marital, prof_edu, prof_course, prof_year,
            prof_occ, prof_emp_status, prof_income, prof_family, prof_land,
            prof_cat, prof_disability, prof_minority, prof_bpl, prof_status
        ]
    )

    # Demo Buttons Wiring
    for d_btn, d_role in [
        (demo_student_btn, "Student"),
        (demo_farmer_btn, "Farmer"),
        (demo_woman_btn, "Woman"),
        (demo_senior_btn, "Senior")
    ]:
        d_evt = d_btn.click(
            fn=lambda r=d_role: handle_demo_login(r),
            inputs=[],
            outputs=[
                session_token, user_info_label, login_status,
                login_view, app_view, tab_admin, main_tabs
            ]
        )
        d_evt.then(
            fn=load_profile_data,
            inputs=[session_token],
            outputs=[
                prof_age, prof_gender, prof_state, prof_district, prof_rural_urban,
                prof_domicile, prof_marital, prof_edu, prof_course, prof_year,
                prof_occ, prof_emp_status, prof_income, prof_family, prof_land,
                prof_cat, prof_disability, prof_minority, prof_bpl, prof_status
            ]
        )

    logout_btn.click(
        fn=handle_logout,
        inputs=[],
        outputs=[
            session_token, user_info_label,
            login_view, app_view, tab_admin
        ]
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
        outputs=[notif_output]
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
    server_port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))
    share_flag = os.getenv("GRADIO_SHARE", "False").lower() in ("true", "1")
    logger.info(f"Starting Gradio UI on {server_name}:{server_port}...")
    demo.launch(server_name=server_name, server_port=server_port, share=share_flag, theme=theme, css=custom_css)
