import re
import streamlit as st
import pandas as pd
from datetime import timedelta
from streamlit_autorefresh import st_autorefresh

from database import (
    create_tables,
    add_export_history,
    track_click,
    get_export_history,
    add_url,
    get_urls,
    get_all_urls,
    update_url_status,
    register_user,
    validate_user,
    change_password,
    start_user_session,
    end_user_session,
    get_users,
    update_user_role,
    get_current_session_duration_seconds,
    get_current_session_click_count,
    get_site_total_click_count,
    get_site_session_click_count,
    get_daily_active_export_rows,
    get_sessions_export_rows
)


# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="AI Web Automation Portal",
    page_icon="🤖",
    layout="wide"
)


# ===============================
# DATABASE SETUP
# ===============================
create_tables()


# ===============================
# SESSION STATE
# ===============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "user_role" not in st.session_state:
    st.session_state.user_role = ""

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home Dashboard"

if "selected_url" not in st.session_state:
    st.session_state.selected_url = None

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

if "register_success_message" not in st.session_state:
    st.session_state.register_success_message = ""

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None


# ===============================
# AUTO REFRESH FOR LIVE SESSION TIMER
# ===============================
if st.session_state.logged_in:
    st_autorefresh(
        interval=1000,
        key="live_session_timer_refresh"
    )


# ===============================
# HELPER FUNCTIONS
# ===============================
def is_valid_email(email):
    email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    if email is None:
        return False

    return re.match(email_pattern, email.strip()) is not None


def format_seconds(seconds):
    try:
        seconds = int(seconds)
    except Exception:
        seconds = 0

    return str(timedelta(seconds=seconds))


def log_click(page_name, control_name, action_name, selected_url=None):
    url_id = None
    url_name = None
    application_name = None

    if selected_url is not None:
        url_id = selected_url.get("URLID")
        url_name = selected_url.get("URLName")
        application_name = selected_url.get("ApplicationName")

    track_click(
        page_name=page_name,
        control_name=control_name,
        action_name=action_name,
        user_email=st.session_state.user_email if st.session_state.user_email else None,
        session_id=st.session_state.current_session_id,
        url_id=url_id,
        url_name=url_name,
        application_name=application_name
    )


def logout_user():
    if st.session_state.current_session_id is not None:
        end_user_session(st.session_state.current_session_id)

    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.user_role = ""
    st.session_state.current_page = "Home Dashboard"
    st.session_state.selected_url = None
    st.session_state.auth_mode = "Login"
    st.session_state.current_session_id = None


def get_selected_site_metrics():
    if st.session_state.selected_url is None:
        return 0, 0

    selected = st.session_state.selected_url
    url_id = selected["URLID"]

    total_site_clicks = get_site_total_click_count(url_id)

    if st.session_state.current_session_id is None:
        session_site_clicks = 0
    else:
        session_site_clicks = get_site_session_click_count(
            url_id=url_id,
            session_id=st.session_state.current_session_id
        )

    return total_site_clicks, session_site_clicks


def build_selected_url_dict(url_row):
    return {
        "URLID": url_row[0],
        "ApplicationName": url_row[1],
        "URLName": url_row[2],
        "URL": url_row[3],
        "Description": url_row[4],
        "Category": url_row[5],
        "IsActive": url_row[6],
        "CreatedDate": url_row[7]
    }


def filter_urls_like_browser(urls, search_text):
    search_value = search_text.lower().strip()

    if search_value == "":
        return []

    starts_with_matches = []
    contains_matches = []

    for row in urls:
        application_name = str(row[1]).lower().strip()
        url_name = str(row[2]).lower().strip()
        website_url = str(row[3]).lower().strip()
        description = str(row[4]).lower().strip()
        category = str(row[5]).lower().strip()

        starts_with_match = (
            url_name.startswith(search_value)
            or application_name.startswith(search_value)
            or website_url.startswith(search_value)
            or category.startswith(search_value)
        )

        contains_match = (
            search_value in url_name
            or search_value in application_name
            or search_value in website_url
            or search_value in description
            or search_value in category
        )

        if starts_with_match:
            starts_with_matches.append(row)

        elif contains_match:
            contains_matches.append(row)

    return starts_with_matches + contains_matches


# ===============================
# LOGIN / REGISTER / ADMIN LOGIN SCREEN
# ===============================
def show_login_screen():
    st.title("AI-Powered Web Automation Portal")
    st.write("Please sign in or register to continue.")
    st.divider()

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        mode_col1, mode_col2, mode_col3 = st.columns(3)

        with mode_col1:
            if st.button("User Login", use_container_width=True):
                st.session_state.auth_mode = "Login"
                st.rerun()

        with mode_col2:
            if st.button("Admin Login", use_container_width=True):
                st.session_state.auth_mode = "Admin Login"
                st.rerun()

        with mode_col3:
            if st.button("Register", use_container_width=True):
                st.session_state.auth_mode = "Register"
                st.rerun()

        st.write("")

        # ===============================
        # USER LOGIN
        # ===============================
        if st.session_state.auth_mode == "Login":
            st.subheader("User Sign In")

            if st.session_state.register_success_message != "":
                st.success(st.session_state.register_success_message)
                st.info("Please login with your registered email and password.")
                st.session_state.register_success_message = ""

            with st.form("login_form", clear_on_submit=True):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")

                login_submitted = st.form_submit_button(
                    "Sign In",
                    use_container_width=True
                )

                if login_submitted:
                    if email.strip() == "":
                        track_click(
                            "Login Screen",
                            "Sign In Button",
                            "Login Failed"
                        )
                        st.error("Email is required.")

                    elif not is_valid_email(email):
                        track_click(
                            "Login Screen",
                            "Sign In Button",
                            "Login Failed"
                        )
                        st.error("Please enter a valid email address.")

                    elif password.strip() == "":
                        track_click(
                            "Login Screen",
                            "Sign In Button",
                            "Login Failed"
                        )
                        st.error("Password is required.")

                    else:
                        is_valid, user = validate_user(email, password)

                        if is_valid:
                            session_id = start_user_session(user["Email"])

                            st.session_state.logged_in = True
                            st.session_state.user_email = user["Email"]
                            st.session_state.user_role = user["Role"]
                            st.session_state.current_page = "Home Dashboard"
                            st.session_state.selected_url = None
                            st.session_state.current_session_id = session_id

                            track_click(
                                "Login Screen",
                                "Sign In Button",
                                "Login Success",
                                user_email=user["Email"],
                                session_id=session_id
                            )

                            st.success("Login successful.")
                            st.rerun()

                        else:
                            track_click(
                                "Login Screen",
                                "Sign In Button",
                                "Login Failed"
                            )

                            st.error("Invalid email or password.")

        # ===============================
        # ADMIN LOGIN
        # ===============================
        elif st.session_state.auth_mode == "Admin Login":
            st.subheader("Admin Sign In")

            st.info("Default Admin: admin@portal.com / Admin@123")

            with st.form("admin_login_form", clear_on_submit=True):
                email = st.text_input("Admin Email")
                password = st.text_input("Admin Password", type="password")

                admin_login_submitted = st.form_submit_button(
                    "Admin Sign In",
                    use_container_width=True
                )

                if admin_login_submitted:
                    if email.strip() == "":
                        track_click(
                            "Admin Login Screen",
                            "Admin Sign In Button",
                            "Login Failed"
                        )
                        st.error("Admin Email is required.")

                    elif not is_valid_email(email):
                        track_click(
                            "Admin Login Screen",
                            "Admin Sign In Button",
                            "Login Failed"
                        )
                        st.error("Please enter a valid admin email address.")

                    elif password.strip() == "":
                        track_click(
                            "Admin Login Screen",
                            "Admin Sign In Button",
                            "Login Failed"
                        )
                        st.error("Admin Password is required.")

                    else:
                        is_valid, user = validate_user(
                            email=email,
                            password=password,
                            required_role="Admin"
                        )

                        if is_valid:
                            session_id = start_user_session(user["Email"])

                            st.session_state.logged_in = True
                            st.session_state.user_email = user["Email"]
                            st.session_state.user_role = user["Role"]
                            st.session_state.current_page = "Home Dashboard"
                            st.session_state.selected_url = None
                            st.session_state.current_session_id = session_id

                            track_click(
                                "Admin Login Screen",
                                "Admin Sign In Button",
                                "Login Success",
                                user_email=user["Email"],
                                session_id=session_id
                            )

                            st.success("Admin login successful.")
                            st.rerun()

                        else:
                            track_click(
                                "Admin Login Screen",
                                "Admin Sign In Button",
                                "Login Failed"
                            )

                            st.error("Invalid admin email or password.")

        # ===============================
        # REGISTER
        # ===============================
        else:
            st.subheader("Register New User")

            with st.form("register_form", clear_on_submit=True):
                full_name = st.text_input("Full Name")
                email = st.text_input("Email Address")
                password = st.text_input("Create Password", type="password")
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password"
                )

                register_submitted = st.form_submit_button(
                    "Register",
                    use_container_width=True
                )

                if register_submitted:
                    if full_name.strip() == "":
                        track_click(
                            "Register Screen",
                            "Register Button",
                            "Registration Failed"
                        )
                        st.error("Full Name is required.")

                    elif email.strip() == "":
                        track_click(
                            "Register Screen",
                            "Register Button",
                            "Registration Failed"
                        )
                        st.error("Email Address is required.")

                    elif not is_valid_email(email):
                        track_click(
                            "Register Screen",
                            "Register Button",
                            "Registration Failed"
                        )
                        st.error("Please enter a valid email address.")

                    elif password.strip() == "":
                        track_click(
                            "Register Screen",
                            "Register Button",
                            "Registration Failed"
                        )
                        st.error("Password is required.")

                    elif confirm_password.strip() == "":
                        track_click(
                            "Register Screen",
                            "Register Button",
                            "Registration Failed"
                        )
                        st.error("Confirm Password is required.")

                    elif password != confirm_password:
                        track_click(
                            "Register Screen",
                            "Register Button",
                            "Registration Failed"
                        )
                        st.error("Password and Confirm Password do not match.")

                    else:
                        success, message = register_user(
                            full_name=full_name,
                            email=email,
                            password=password
                        )

                        if success:
                            track_click(
                                "Register Screen",
                                "Register Button",
                                "User Registered"
                            )

                            st.session_state.register_success_message = message
                            st.session_state.auth_mode = "Login"
                            st.rerun()

                        else:
                            track_click(
                                "Register Screen",
                                "Register Button",
                                "Registration Failed"
                            )

                            st.error(message)


# ===============================
# SIDEBAR MENU
# ===============================
def show_sidebar():
    st.sidebar.title("Automation Portal")

    st.sidebar.write("Signed in as:")
    st.sidebar.write(f"**{st.session_state.user_email}**")

    st.sidebar.write("Role:")
    st.sidebar.write(f"**{st.session_state.user_role}**")

    if st.session_state.current_session_id is not None:
        st.sidebar.write("Session ID:")
        st.sidebar.write(f"**{st.session_state.current_session_id}**")

    st.sidebar.divider()

    if st.sidebar.button("Home Dashboard", use_container_width=True):
        st.session_state.current_page = "Home Dashboard"
        log_click("Sidebar", "Home Dashboard", "Clicked")
        st.rerun()

    if st.session_state.user_role == "Admin":
        if st.sidebar.button("URL Management", use_container_width=True):
            st.session_state.current_page = "URL Management"
            log_click("Sidebar", "URL Management", "Clicked")
            st.rerun()

        if st.sidebar.button("Admin Management", use_container_width=True):
            st.session_state.current_page = "Admin Management"
            log_click("Sidebar", "Admin Management", "Clicked")
            st.rerun()

    if st.sidebar.button("Export History", use_container_width=True):
        st.session_state.current_page = "Export History"
        log_click("Sidebar", "Export History", "Clicked")
        st.rerun()

    if st.sidebar.button("Data Export", use_container_width=True):
        st.session_state.current_page = "Data Export"
        log_click("Sidebar", "Data Export", "Clicked")
        st.rerun()

    if st.sidebar.button("Change Password", use_container_width=True):
        st.session_state.current_page = "Change Password"
        log_click("Sidebar", "Change Password", "Clicked")
        st.rerun()

    st.sidebar.divider()

    if st.sidebar.button("Logout", use_container_width=True):
        log_click("Sidebar", "Logout Button", "Clicked")
        logout_user()
        st.rerun()


# ===============================
# HOME DASHBOARD
# ===============================
def show_home_dashboard():
    st.title("AI-Powered Web Automation Portal")
    st.write("Automate website report downloads using Python and Playwright.")

    st.divider()

    history = get_export_history()
    total_exports = len(history)
    url_count = len(get_urls())

    session_seconds = 0
    session_clicks = 0

    if st.session_state.current_session_id is not None:
        session_seconds = get_current_session_duration_seconds(
            st.session_state.current_session_id
        )

        session_clicks = get_current_session_click_count(
            st.session_state.current_session_id
        )

    metric1, metric2, metric3, metric4 = st.columns(4)

    with metric1:
        st.metric("Saved Active URLs", url_count)

    with metric2:
        st.metric("Current Session Clicks", session_clicks)

    with metric3:
        st.metric("Live Session Time Spent", format_seconds(session_seconds))

    with metric4:
        st.metric("Total Export Events", total_exports)

    st.divider()

    # ===============================
    # SEARCH URLS - BROWSER STYLE
    # ===============================
    st.subheader("Search URL")

    search_text = st.text_input(
        "Start typing URL name or website address",
        placeholder="Example: youtube, google, sharepoint"
    )

    urls = get_urls()
    matching_urls = filter_urls_like_browser(urls, search_text)

    if search_text.strip() == "":
        st.info("Start typing to search. No URLs will be shown until you type.")
    else:
        if len(matching_urls) == 0:
            st.warning("No matching URLs found.")
        else:
            st.caption(f"{len(matching_urls)} matching result(s) found")

            for url_row in matching_urls:
                selected_url_obj = build_selected_url_dict(url_row)

                with st.container(border=True):
                    col1, col2 = st.columns([5, 1])

                    with col1:
                        st.markdown(
                            f"**{selected_url_obj['URLName']}**  \n"
                            f"{selected_url_obj['URL']}"
                        )

                    with col2:
                        if st.button(
                            "Select",
                            key=f"select_url_{selected_url_obj['URLID']}",
                            use_container_width=True
                        ):
                            st.session_state.selected_url = selected_url_obj

                            log_click(
                                "Home Dashboard",
                                f"Selected URL - {selected_url_obj['URLName']}",
                                "Clicked",
                                selected_url_obj
                            )

                            add_export_history(
                                report_name=selected_url_obj["URLName"],
                                status="URL Selected",
                                file_path=selected_url_obj["URL"],
                                email_status="Not Sent"
                            )

                            st.success(f"{selected_url_obj['URLName']} selected.")
                            st.rerun()

    st.divider()

    # ===============================
    # SELECTED SITE INFORMATION
    # ===============================
    st.subheader("Selected Site Information")

    if st.session_state.selected_url is None:
        st.info("No site selected yet. Search and select a URL above.")
    else:
        selected = st.session_state.selected_url

        total_site_clicks, session_site_clicks = get_selected_site_metrics()

        site_metric1, site_metric2, site_metric3 = st.columns(3)

        with site_metric1:
            st.metric("Selected Site Total Clicks", total_site_clicks)

        with site_metric2:
            st.metric("Selected Site Session Clicks", session_site_clicks)

        with site_metric3:
            st.metric("Current Session ID", st.session_state.current_session_id)

        with st.container(border=True):
            st.markdown(f"### {selected['URLName']}")

            info_col1, info_col2 = st.columns(2)

            with info_col1:
                st.write(f"**Application Name:** {selected['ApplicationName']}")
                st.write(f"**Category:** {selected['Category']}")
                st.write(
                    f"**Status:** {'Active' if selected['IsActive'] == 1 else 'Inactive'}"
                )

            with info_col2:
                st.write(f"**URL ID:** {selected['URLID']}")
                st.write(f"**Created Date:** {selected['CreatedDate']}")
                st.write(f"**Website URL:** {selected['URL']}")

            st.write("**Description:**")
            st.write(selected["Description"])

        st.write("")

        action1, action2, action3 = st.columns(3)

        with action1:
            if st.button("Track Open Site Click", use_container_width=True):
                log_click(
                    "Selected Site Information",
                    f"Open Site - {selected['URLName']}",
                    "Clicked",
                    selected
                )

                add_export_history(
                    report_name=selected["URLName"],
                    status="Site Open Clicked",
                    file_path=selected["URL"],
                    email_status="Not Sent"
                )

                st.success("Open site click captured.")

            st.link_button(
                "Open Selected Site",
                selected["URL"],
                use_container_width=True
            )

        with action2:
            if st.button("Run Session Playlist", use_container_width=True):
                log_click(
                    "Selected Site Information",
                    f"Run Session Playlist - {selected['URLName']}",
                    "Clicked",
                    selected
                )

                add_export_history(
                    report_name="Session Playlist",
                    status="Clicked",
                    file_path=selected["URL"],
                    email_status="Not Sent"
                )

                st.success(
                    "Session Playlist click captured. Automation will be connected later."
                )
                st.rerun()

        with action3:
            if st.button("Run User Trends", use_container_width=True):
                log_click(
                    "Selected Site Information",
                    f"Run User Trends - {selected['URLName']}",
                    "Clicked",
                    selected
                )

                add_export_history(
                    report_name="User Trends",
                    status="Clicked",
                    file_path=selected["URL"],
                    email_status="Not Sent"
                )

                st.success(
                    "User Trends click captured. Automation will be connected later."
                )
                st.rerun()

        if st.button("Clear Selected Site", use_container_width=True):
            log_click(
                "Selected Site Information",
                "Clear Selected Site",
                "Clicked",
                selected
            )

            st.session_state.selected_url = None
            st.rerun()


# ===============================
# URL MANAGEMENT - ADMIN ONLY
# ===============================
def show_url_management():
    if st.session_state.user_role != "Admin":
        st.error("Access denied. Only admins can add or manage URLs.")
        return

    st.title("URL Management")
    st.write("Add and manage report URLs used by the automation portal.")

    st.divider()

    st.subheader("Add New URL")

    with st.form("add_url_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            application_name = st.text_input("Application Name")
            url_name = st.text_input("URL Name")

        with col2:
            category = st.selectbox(
                "Category",
                ["Report", "Analytics", "Admin", "Dashboard", "Other"]
            )
            url = st.text_input("Website URL")

        description = st.text_area("Description")

        submitted = st.form_submit_button("Save URL", use_container_width=True)

        if submitted:
            if application_name.strip() == "":
                st.error("Application Name is required.")

            elif url_name.strip() == "":
                st.error("URL Name is required.")

            elif url.strip() == "":
                st.error("Website URL is required.")

            else:
                add_url(
                    application_name=application_name,
                    url_name=url_name,
                    url=url,
                    description=description,
                    category=category
                )

                log_click("URL Management", "Save URL Button", "Clicked")

                st.success("URL saved successfully.")
                st.rerun()

    st.divider()

    st.subheader("Manage Saved URLs")

    urls = get_all_urls()

    if len(urls) == 0:
        st.write("No URLs saved yet.")
    else:
        df = pd.DataFrame(
            urls,
            columns=[
                "URL ID",
                "Application Name",
                "URL Name",
                "URL",
                "Description",
                "Category",
                "Is Active",
                "Created Date"
            ]
        )

        df["Is Active"] = df["Is Active"].apply(lambda value: True if value == 1 else False)

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=[
                "URL ID",
                "Application Name",
                "URL Name",
                "URL",
                "Description",
                "Category",
                "Created Date"
            ],
            column_config={
                "Is Active": st.column_config.CheckboxColumn(
                    "Is Active",
                    help="Tick to make this URL available to users.",
                    default=True
                )
            }
        )

        if st.button("Save URL Status Changes", use_container_width=True):
            for _, row in edited_df.iterrows():
                update_url_status(
                    url_id=int(row["URL ID"]),
                    is_active=1 if bool(row["Is Active"]) else 0
                )

            log_click(
                "URL Management",
                "Save URL Status Changes Button",
                "URL Status Updated"
            )

            st.success("URL status updated successfully.")
            st.rerun()


# ===============================
# ADMIN MANAGEMENT
# ===============================
def show_admin_management():
    if st.session_state.user_role != "Admin":
        st.error("Access denied. Only admins can manage admins.")
        return

    st.title("Admin Management")
    st.write("Select which registered users should have Admin access.")

    st.divider()

    users = get_users()

    if len(users) == 0:
        st.write("No users found.")
        return

    df = pd.DataFrame(
        users,
        columns=[
            "User ID",
            "Full Name",
            "Email",
            "Role",
            "Is Active",
            "Created Date"
        ]
    )

    df["Is Admin"] = df["Role"].apply(lambda role: True if role == "Admin" else False)

    st.info(
        "Tick the checkbox to make a user Admin. Untick it to remove Admin access. "
        "You cannot remove your own Admin access."
    )

    edited_df = st.data_editor(
        df[
            [
                "User ID",
                "Full Name",
                "Email",
                "Role",
                "Is Admin",
                "Is Active",
                "Created Date"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        disabled=[
            "User ID",
            "Full Name",
            "Email",
            "Role",
            "Is Active",
            "Created Date"
        ],
        column_config={
            "Is Admin": st.column_config.CheckboxColumn(
                "Is Admin",
                help="Select to give Admin access",
                default=False
            )
        }
    )

    st.write("")

    if st.button("Save Admin Changes", use_container_width=True):
        has_error = False

        for _, row in edited_df.iterrows():
            email = str(row["Email"]).lower().strip()
            is_admin_checked = bool(row["Is Admin"])

            if (
                email == st.session_state.user_email.lower().strip()
                and not is_admin_checked
            ):
                has_error = True
                st.error("You cannot remove your own Admin access.")
                break

        if not has_error:
            for _, row in edited_df.iterrows():
                user_id = int(row["User ID"])
                is_admin_checked = bool(row["Is Admin"])

                new_role = "Admin" if is_admin_checked else "User"

                update_user_role(
                    user_id=user_id,
                    role=new_role
                )

            log_click(
                "Admin Management",
                "Save Admin Changes Button",
                "Admin Roles Updated"
            )

            st.success("Admin access updated successfully.")
            st.rerun()


# ===============================
# EXPORT HISTORY PAGE
# ===============================
def show_export_history():
    st.title("Export History")
    st.write("View report export history and automation status.")

    st.divider()

    history = get_export_history()

    if len(history) == 0:
        st.write("No exports yet.")
    else:
        df = pd.DataFrame(
            history,
            columns=[
                "Report Name",
                "Export Date",
                "Status",
                "File Path",
                "Email Status"
            ]
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# ===============================
# DATA EXPORT PAGE
# ===============================
def show_data_export():
    st.title("Data Export")
    st.write("Export portal analytics in the same format as uploaded CSV files.")

    st.divider()

    st.subheader("Daily Active Users Export")

    daily_rows = get_daily_active_export_rows()

    daily_df = pd.DataFrame(
        daily_rows,
        columns=[
            "Date",
            "DailyActiveUsers",
            "WeeklyActiveUsers"
        ]
    )

    st.dataframe(
        daily_df,
        use_container_width=True,
        hide_index=True
    )

    daily_csv = daily_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Daily Active Users CSV",
        data=daily_csv,
        file_name="SearchieDailyActives_DAA-Cloud-Sharepoint-Sessions.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.divider()

    st.subheader("Sessions Export")

    session_rows = get_sessions_export_rows()

    sessions_df = pd.DataFrame(
        session_rows,
        columns=[
            "Created",
            "Uid",
            "Name",
            "Email",
            "LastPage",
            "NumSessions",
            "LastSessionTime",
            "LastSessionSec",
            "LastSessionActiveSec",
            "LastSessionNumPages",
            "LastSessionNumEvents",
            "LastBrowser",
            "LastDevice",
            "LastOperatingSystem",
            "TotalSec",
            "TotalActiveSec",
            "AvgSessionSec",
            "AvgSessionActiveSec",
            "NumEvents",
            "LastMatchingIp",
            "LastMatchingLatLong",
            "LastMatchingSessionLink"
        ]
    )

    st.dataframe(
        sessions_df,
        use_container_width=True,
        hide_index=True
    )

    sessions_csv = sessions_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Sessions CSV",
        data=sessions_csv,
        file_name="DAA_Cloud___Sharepoint___Sessions.csv",
        mime="text/csv",
        use_container_width=True
    )


# ===============================
# CHANGE PASSWORD PAGE
# ===============================
def show_change_password():
    st.title("Change Password")
    st.write("Update your account password.")

    st.divider()

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        with st.form("change_password_form", clear_on_submit=True):
            current_password = st.text_input(
                "Current Password",
                type="password"
            )

            new_password = st.text_input(
                "New Password",
                type="password"
            )

            confirm_new_password = st.text_input(
                "Confirm New Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Change Password",
                use_container_width=True
            )

            if submitted:
                if current_password.strip() == "":
                    st.error("Current Password is required.")

                elif new_password.strip() == "":
                    st.error("New Password is required.")

                elif confirm_new_password.strip() == "":
                    st.error("Confirm New Password is required.")

                elif new_password != confirm_new_password:
                    st.error("New Password and Confirm New Password do not match.")

                elif current_password == new_password:
                    st.error("New Password cannot be the same as Current Password.")

                else:
                    success, message = change_password(
                        email=st.session_state.user_email,
                        old_password=current_password,
                        new_password=new_password
                    )

                    if success:
                        log_click(
                            "Change Password",
                            "Change Password Button",
                            "Password Changed"
                        )

                        st.success(message)

                        logout_user()
                        st.rerun()

                    else:
                        log_click(
                            "Change Password",
                            "Change Password Button",
                            "Password Change Failed"
                        )

                        st.error(message)


# ===============================
# APP START
# ===============================
if st.session_state.logged_in:
    show_sidebar()

    if st.session_state.current_page == "Home Dashboard":
        show_home_dashboard()

    elif st.session_state.current_page == "URL Management":
        show_url_management()

    elif st.session_state.current_page == "Admin Management":
        show_admin_management()

    elif st.session_state.current_page == "Export History":
        show_export_history()

    elif st.session_state.current_page == "Data Export":
        show_data_export()

    elif st.session_state.current_page == "Change Password":
        show_change_password()

else:
    show_login_screen()