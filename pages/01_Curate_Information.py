import streamlit as st
import io
import os
import time
from pathlib import Path
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Curate Information", page_icon="📋", layout="wide")

# Sidebar logo - responsive to sidebar width
logo_path = Path(__file__).parent.parent / "resources" / "iitj.jpg"
if logo_path.exists():
    st.sidebar.markdown(
        f'''<style>
        .sidebar .element-container img {{
            width: 100% !important;
            max-width: 250px;
            height: auto;
        }}
        </style>''',
        unsafe_allow_html=True
    )
    st.sidebar.image(str(logo_path), use_container_width=True)
    st.sidebar.markdown("---")

st.title(":material/description: Upload documents to IITJ Smart Search")
st.caption("Upload any file, store and search")

# Footer - placed early to ensure it always renders
footer = """<style>
.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
background-color: #2C1E5B;
color: white;
text-align: center;
z-index: 9999;
padding: 10px 0;
box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
}
.footer p {
margin: 0;
}
.footer a {
color: white;
text-decoration: none;
}
.footer a:hover {
text-decoration: underline;
}
</style>
<div class="footer">
<p>Developed with ❤️ by <a style='display: inline; text-align: center;' href="https://bit.ly/atozaboutdata" target="_blank">MAHANTESH HIREMATH(M25AI2134@IITJ.AC.IN)</a></p>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)

st.markdown("---")

# Snowflake connection (reuse session from Home.py if available)
def get_or_refresh_session():
    if "get_snowflake_session" in st.session_state:
        session = st.session_state.get_snowflake_session()
        try:
            session.sql("SELECT 1").collect()
        except Exception:
            session = st.session_state.get_snowflake_session()
        st.session_state.snowflake_session = session
        return session

    if "default_session" in st.session_state:
        try:
            st.session_state.default_session.sql("SELECT 1").collect()
            return st.session_state.default_session
        except Exception:
            del st.session_state.default_session

    try:
        session = get_active_session()
        session.sql("SELECT 1").collect()
    except Exception:
        from snowflake.snowpark import Session
        connections = st.secrets.get("connections", {})
        cfg = connections.get("my_example_connection") or connections.get("snowflake")
        if not cfg:
            raise Exception("No Snowflake connection configured in secrets.toml")
        session = Session.builder.configs(cfg).create()
        session.sql("SELECT 1").collect()

    st.session_state.default_session = session
    return session

session = get_or_refresh_session()

with st.sidebar:
    try:
        version = session.sql("SELECT CURRENT_VERSION()").collect()[0][0]
        st.success(f"connected to ☁️")
    except Exception as exc:
        st.error(f"Snowflake connection failed: {exc}")
        st.stop()

# Default configuration
DATABASE = "IITJ"
SCHEMA = "MH"
TABLE_NAME = "UPLOADED_FILES_METADATA"
AUTH_TABLE = "IITJ_DOCUMENT_CURATOR_INFO"
FULL_STAGE_NAME = f"{DATABASE}.{SCHEMA}.IITJ_INFO_STAGE"
STAGE_NAME = f"@{FULL_STAGE_NAME}"

# Authentication function
def authenticate_user(email: str, password: str) -> bool:
    """Verify user credentials against the Snowflake table"""
    try:
        auth_query = f"""
        SELECT COUNT(*) as count
        FROM {DATABASE}.{SCHEMA}.{AUTH_TABLE}
        WHERE UER_EMAIL = ? AND PASSWORD = ?
        """
        result = session.sql(auth_query, params=[email, password]).collect()
        return result[0]['COUNT'] > 0
    except Exception as exc:
        st.error(f"Authentication error: {exc}")
        return False

def run_sql_with_refresh(sql: str):
    global session
    try:
        return session.sql(sql).collect()
    except Exception:
        session = get_or_refresh_session()
        return session.sql(sql).collect()

def ensure_stage_and_table():
    run_sql_with_refresh(
        f"""
        CREATE STAGE IF NOT EXISTS {FULL_STAGE_NAME}
        ENCRYPTION = ( TYPE = 'SNOWFLAKE_SSE' )
        DIRECTORY = ( ENABLE = true )
        """
    )

    run_sql_with_refresh(
        f"""
        CREATE TABLE IF NOT EXISTS {DATABASE}.{SCHEMA}.{TABLE_NAME} (
            DOC_ID NUMBER AUTOINCREMENT,
            FILE_NAME VARCHAR,
            SHORT_DESCRIPTION VARCHAR,
            SOURCE_URL VARCHAR,
            FILE_TYPE VARCHAR,
            FILE_SIZE NUMBER,
            UPLOADED_BY VARCHAR,
            UPLOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
    )

ensure_stage_and_table()

with st.container(border=True):
    st.subheader(":material/table: Uploaded Files Metadata")

    col1, col2, col3 = st.columns(3)
    with col1:
        name_filter = st.text_input("File name contains", placeholder="e.g., faculty")
    with col2:
        uploader_filter = st.text_input("Uploaded by", value="m25ai2134@iitj.ac.in")
    with col3:
        url_filter = st.text_input("Source URL contains", placeholder="e.g., iitj.ac.in")

    limit = st.slider("Rows", min_value=1, max_value=200, value=25)

    if st.button(":material/refresh: Refresh results"):
        pass

    where_clauses = []
    params = []

    if name_filter.strip():
        where_clauses.append("FILE_NAME ILIKE ?")
        params.append(f"%{name_filter.strip()}%")

    if uploader_filter.strip():
        where_clauses.append("UPLOADED_BY ILIKE ?")
        params.append(f"%{uploader_filter.strip()}%")

    if url_filter.strip():
        where_clauses.append("SOURCE_URL ILIKE ?")
        params.append(f"%{url_filter.strip()}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query_sql = f"""
    SELECT
        FILE_NAME,
        SHORT_DESCRIPTION,
        SOURCE_URL,
        FILE_TYPE,
        FILE_SIZE,
        UPLOADED_BY,
        UPLOAD_TIMESTAMP
    FROM {DATABASE}.{SCHEMA}.{TABLE_NAME}
    {where_sql}
    ORDER BY UPLOAD_TIMESTAMP DESC
    LIMIT {limit}
    """

    try:
        rows = session.sql(query_sql, params=params).collect()
        data = [r.as_dict() if hasattr(r, "as_dict") else dict(r) for r in rows]
        st.dataframe(data, width="stretch", hide_index=True)
    except Exception as exc:
        st.error(f"Query failed: {exc}")

st.markdown("---")

# Authentication Section
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# Login/Logout in sidebar
with st.sidebar:
    st.markdown("---")
    if st.session_state.authenticated:
        st.success(f"🔓 Logged in as: {st.session_state.user_email}")
        if st.button("🔒 Logout"):
            st.session_state.authenticated = False
            st.session_state.user_email = ""
            st.rerun()
    else:
        st.warning("🔒 Login required to upload files")

with st.container(border=True):
    st.subheader(":material/upload: Upload a file")
    
    # Show login form if not authenticated
    if not st.session_state.authenticated:
        st.info("Please login to upload files")
        
        with st.form("login_form"):
            login_email = st.text_input("Email", placeholder="your.email@iitj.ac.in")
            login_password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("🔓 Login", type="primary")
            
            if login_submit:
                if not login_email.strip() or not login_password.strip():
                    st.error("Please enter both email and password")
                else:
                    if authenticate_user(login_email.strip(), login_password.strip()):
                        st.session_state.authenticated = True
                        st.session_state.user_email = login_email.strip()
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
        st.stop()

    # Upload form (only shown if authenticated)
    st.success(f"Logged in as: {st.session_state.user_email}")
    
    uploaded_by = st.text_input("Uploaded by", value=st.session_state.user_email, disabled=True)
    short_description = st.text_input(
        "Short description",
        placeholder="Brief description (optional)",
        help="If left empty, file name will be used."
    )
    source_url = st.text_input(
        "Source URL",
        placeholder="https://...",
        help="Provide the source link for this document."
    )

    uploaded_file = st.file_uploader(
        "Choose a file",
        help="Any file type is supported."
    )

    if uploaded_file:
        st.write(f"**File:** {uploaded_file.name}")
        st.write(f"**Size:** {uploaded_file.size / (1024 * 1024):.2f} MB")

    if st.button(":material/cloud_upload: Upload to ☁️", type="primary"):
        if not st.session_state.authenticated:
            st.error("Please login to upload files.")
            st.stop()
        if not uploaded_file:
            st.error("Please choose a file to upload.")
            st.stop()
        if not source_url.strip():
            st.error("Please provide the source URL.")
            st.stop()

        file_name = uploaded_file.name
        file_ext = os.path.splitext(file_name)[1].lstrip(".")
        file_size = uploaded_file.size
        description = short_description.strip() or file_name

        with st.spinner(":material/upload: Uploading files to ☁️..."):
            try:
                staged_name = file_name
                file_stream = io.BytesIO(uploaded_file.getvalue())
                session.file.put_stream(
                    file_stream,
                    f"{STAGE_NAME}/{staged_name}",
                    overwrite=True,
                    auto_compress=False,
                )
            except Exception as exc:
                st.error(f"Upload failed: {exc}")
                st.stop()

        with st.spinner(":material/database: Writing metadata to ☁️..."):
            try:
                insert_sql = f"""
                INSERT INTO {DATABASE}.{SCHEMA}.{TABLE_NAME}
                (FILE_NAME, SHORT_DESCRIPTION, SOURCE_URL, FILE_TYPE, FILE_SIZE, UPLOADED_BY)
                SELECT
                    ?, ?, ?, ?, ?, ?
                """
                session.sql(
                    insert_sql,
                    params=[
                        file_name,
                        description,
                        source_url.strip(),
                        file_ext,
                        file_size,
                        st.session_state.user_email,
                    ],
                ).collect()
                st.success("File uploaded and metadata saved.")
            except Exception as exc:
                st.error(f"Metadata insert failed: {exc}")
                st.stop()

        with st.spinner(":material/auto_awesome: Generating embeddings..."):
            try:
                session.sql(f"LIST {STAGE_NAME}").collect()
                session.sql(
                    "CALL IITJ.MH.GENERATE_EMBEDDINGS_FOR_NEW_FILE(?)",
                    params=[file_name],
                ).collect()
                st.success(f"Embeddings generated for {file_name}. You can start searching now!")
            except Exception as exc:
                st.error(f"Embedding generation failed: {exc}")
