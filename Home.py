import streamlit as st
from pathlib import Path

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

# Pages
curate = st.Page("pages/01_Curate_Information.py", title="Curate Information", icon="📋", default=True)
ai_search = st.Page("pages/02_AI_Search.py", title="AI Search", icon="🔍")

# Navigation
pg = st.navigation({
    "Menu": [curate, ai_search]
})

pg.run()
