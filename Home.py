import streamlit as st

st.logo(
    image="https://upload.wikimedia.org/wikipedia/en/4/41/Flag_of_India.svg",
    link="https://www.linkedin.com/in/mahantesh-hiremath/",
    icon_image="https://upload.wikimedia.org/wikipedia/en/4/41/Flag_of_India.svg"
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
