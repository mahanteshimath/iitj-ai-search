import streamlit as st
from pathlib import Path
from snowflake.snowpark.context import get_active_session

# IITJ Logo
logo_path = Path(__file__).parent / "resources" / "iitj.jpg"
if logo_path.exists():
    st.logo(
        image=str(logo_path),
        link="https://www.iitj.ac.in/",
        icon_image=str(logo_path)
    )

st.set_page_config(
    page_title="IIT JODHPUR SMART SEARCH",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Snowflake session at app startup
def get_snowflake_session():
    """Get active Snowflake session or create new one if expired"""
    try:
        # Try to get active session (works in Streamlit in Snowflake)
        session = get_active_session()
        return session
    except Exception:
        # For local/cloud deployment, use session from secrets
        from snowflake.snowpark import Session
        if "snowflake_session" in st.session_state:
            # Test if existing session is still valid
            try:
                st.session_state.snowflake_session.sql("SELECT 1").collect()
                return st.session_state.snowflake_session
            except Exception:
                # Session expired, remove it
                del st.session_state.snowflake_session
        
        # Create new session
        new_session = Session.builder.configs(st.secrets["connections"]["snowflake"]).create()
        st.session_state.snowflake_session = new_session
        return new_session

# Establish connection at app launch
if "snowflake_session" not in st.session_state:
    with st.spinner("🔌 Connecting to Snowflake..."):
        st.session_state.snowflake_session = get_snowflake_session()
        st.session_state.get_snowflake_session = get_snowflake_session
    st.balloons()
    st.toast("✅ Connected to Snowflake!", icon="✅")

# Pages
curate = st.Page("pages/01_Curate_Information.py", title="Curate Information", icon="📋", default=True)
ai_search = st.Page("pages/02_AI_Search.py", title="AI Search", icon="🔍")

# Navigation
pg = st.navigation({
    "Menu": [curate, ai_search]
})

pg.run()
