import streamlit as st
import pandas as pd
from database import (
    create_tables,
    add_export_history,
    track_click,
    get_export_history,
    add_url,
    get_urls
)
from automation import open_selected_url


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

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home Dashboard"
if "selected_url" not in st.session_state:
    st.session_state.selected_url = None

# ===============================
# LOGIN SCREEN
# ===============================
def show_login_screen():
    st.title("AI-Powered Web Automation Portal")
    st.write("Please sign in to continue.")
    st.divider()

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.subheader("Sign In")

        username = st.text_input("Username / Email")
        password = st.text_input("Password", type="password")

        if st.button("Sign In", use_container_width=True):
            if username == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.session_state.user_email = username
                st.session_state.current_page = "Home Dashboard"

                track_click("Login Screen", "Sign In Button", "Login Success")

                st.success("Login successful.")
                st.rerun()
            else:
                track_click("Login Screen", "Sign In Button", "Login Failed")
                st.error("Invalid username or password.")


# ===============================
# SIDEBAR MENU
# ===============================
def show_sidebar():
    st.sidebar.title("Automation Portal")

    st.sidebar.write("Signed in as:")
    st.sidebar.write(f"**{st.session_state.user_email}**")

    st.sidebar.divider()

    if st.sidebar.button("Home Dashboard", use_container_width=True):
        st.session_state.current_page = "Home Dashboard"
        track_click("Sidebar", "Home Dashboard", "Clicked")
        st.rerun()

    if st.sidebar.button("URL Management", use_container_width=True):
        st.session_state.current_page = "URL Management"
        track_click("Sidebar", "URL Management", "Clicked")
        st.rerun()

    if st.sidebar.button("Export History", use_container_width=True):
        st.session_state.current_page = "Export History"
        track_click("Sidebar", "Export History", "Clicked")
        st.rerun()

    st.sidebar.divider()

    if st.sidebar.button("Logout", use_container_width=True):
        track_click("Sidebar", "Logout Button", "Clicked")
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.current_page = "Home Dashboard"
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
    successful_exports = len([row for row in history if row[2] == "Completed"])
    failed_exports = len([row for row in history if row[2] == "Failed"])
    url_count = len(get_urls())

    metric1, metric2, metric3, metric4 = st.columns(4)

    with metric1:
        st.metric("Total Exports / Clicks", total_exports)

    with metric2:
        st.metric("Saved URLs", url_count)

    with metric3:
        st.metric("Successful Exports", successful_exports)

    with metric4:
        st.metric("Failed Exports", failed_exports)

    st.divider()

    # ===============================
    # SEARCH URLS
    # ===============================
    st.subheader("Search URLs")

    search_text = st.text_input(
        "Search by URL name, application, category, or description"
    )

    urls = get_urls()

    if search_text.strip() != "":
        matching_urls = [
            row for row in urls
            if search_text.lower() in str(row[1]).lower()
            or search_text.lower() in str(row[2]).lower()
            or search_text.lower() in str(row[4]).lower()
            or search_text.lower() in str(row[5]).lower()
        ]

        if len(matching_urls) == 0:
            st.warning("No matching URLs found.")
        else:
            st.write("Matching URLs:")

            for url_row in matching_urls:
                url_id = url_row[0]
                application_name = url_row[1]
                url_name = url_row[2]
                website_url = url_row[3]
                description = url_row[4]
                category = url_row[5]
                is_active = url_row[6]
                created_date = url_row[7]

                with st.container(border=True):
                    st.write(f"**{url_name}**")
                    st.write(f"Application: {application_name}")
                    st.write(f"Category: {category}")
                    st.write(description)
                    st.write(website_url)

                    if st.button(
                        f"Select {url_name}",
                        key=f"select_url_{url_id}",
                        use_container_width=True
                    ):
                        st.session_state.selected_url = {
                            "URLID": url_id,
                            "ApplicationName": application_name,
                            "URLName": url_name,
                            "URL": website_url,
                            "Description": description,
                            "Category": category,
                            "IsActive": is_active,
                            "CreatedDate": created_date
                        }

                        track_click(
                            "Home Dashboard",
                            f"Selected URL - {url_name}",
                            "Clicked"
                        )

                        add_export_history(
                            report_name=url_name,
                            status="URL Selected",
                            file_path=website_url,
                            email_status="Not Sent"
                        )

                        st.success(f"{url_name} selected.")
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

        with st.container(border=True):
            st.markdown(f"### {selected['URLName']}")

            info_col1, info_col2 = st.columns(2)

            with info_col1:
                st.write(f"**Application Name:** {selected['ApplicationName']}")
                st.write(f"**Category:** {selected['Category']}")
                st.write(f"**Status:** {'Active' if selected['IsActive'] == 1 else 'Inactive'}")

            with info_col2:
                st.write(f"**URL ID:** {selected['URLID']}")
                st.write(f"**Created Date:** {selected['CreatedDate']}")
                st.write(f"**Website URL:** {selected['URL']}")

            st.write("**Description:**")
            st.write(selected["Description"])

        st.write("")

        action1, action2, action3 = st.columns(3)

        with action1:
            if st.button("Open Selected Site", use_container_width=True):
                track_click(
                    "Selected Site Information",
                    f"Open Site - {selected['URLName']}",
                    "Clicked"
                )

                add_export_history(
                    report_name=selected["URLName"],
                    status="Opening Site",
                    file_path=selected["URL"],
                    email_status="Not Sent"
                )

                st.info("Opening selected site in Playwright browser...")

                open_selected_url(selected["URL"])

                add_export_history(
                    report_name=selected["URLName"],
                    status="Site Opened",
                    file_path=selected["URL"],
                    email_status="Not Sent"
                )

                st.success("Selected site opened successfully.")
                st.rerun()

        with action2:
            if st.button("Run Session Playlist", use_container_width=True):
                track_click(
                    "Selected Site Information",
                    f"Run Session Playlist - {selected['URLName']}",
                    "Clicked"
                )

                add_export_history(
                    report_name="Session Playlist",
                    status="Clicked",
                    file_path=selected["URL"],
                    email_status="Not Sent"
                )

                st.success("Session Playlist click captured. Automation will be connected later.")
                st.rerun()

        with action3:
            if st.button("Run User Trends", use_container_width=True):
                track_click(
                    "Selected Site Information",
                    f"Run User Trends - {selected['URLName']}",
                    "Clicked"
                )

                add_export_history(
                    report_name="User Trends",
                    status="Clicked",
                    file_path=selected["URL"],
                    email_status="Not Sent"
                )

                st.success("User Trends click captured. Automation will be connected later.")
                st.rerun()

        if st.button("Clear Selected Site", use_container_width=True):
            track_click(
                "Selected Site Information",
                "Clear Selected Site",
                "Clicked"
            )

            st.session_state.selected_url = None
            st.rerun()


# ===============================
# URL MANAGEMENT
# ===============================
def show_url_management():
    st.title("URL Management")
    st.write("Add and manage report URLs used by Playwright automation.")

    st.divider()

    st.subheader("Add New URL")

    with st.form("add_url_form"):
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

                track_click("URL Management", "Save URL Button", "Clicked")

                st.success("URL saved successfully.")
                st.rerun()

    st.divider()

    st.subheader("Saved URLs")

    urls = get_urls()

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

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


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
# APP START
# ===============================
if st.session_state.logged_in:
    show_sidebar()

    if st.session_state.current_page == "Home Dashboard":
        show_home_dashboard()

    elif st.session_state.current_page == "URL Management":
        show_url_management()

    elif st.session_state.current_page == "Export History":
        show_export_history()

else:
    show_login_screen()