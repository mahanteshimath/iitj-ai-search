import streamlit as st
import os
import io
from pathlib import Path
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Curate Information", page_icon="📋", layout="wide")

# Sidebar logo
logo_path = Path(__file__).parent.parent / "resources" / "iitj.jpg"
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)
    st.sidebar.markdown("---")

st.title(":material/description: Document Metadata Uploader")
st.caption("Upload any file and store metadata in Snowflake")
st.markdown("---")

# Connect to Snowflake
try:
    session = get_active_session()
except Exception:
    from snowflake.snowpark import Session
    session = Session.builder.configs(st.secrets["connections"]["snowflake"]).create()

st.subheader("🧾 Metadata Settings")

col1, col2, col3 = st.columns(3)
with col1:
    uploaded_by = st.text_input("Uploaded By", value="m25ai2134@iitj.ac.in")
with col2:
    source_url = st.text_input("Source URL", placeholder="https://...")
with col3:
    auto_compress = st.checkbox("Auto-compress files", value=False, 
                                  help="Enable gzip compression for uploaded files")

default_short_description = st.text_input(
    "Default Short Description",
    placeholder="Optional default description for all files"
)

st.subheader("📁 Upload File")
uploaded_file = st.file_uploader(
    "Choose a file",
    type=None,
    accept_multiple_files=False
)

short_description = default_short_description
if uploaded_file:
    st.markdown("### 📝 File Description")
    short_description = st.text_input(
        f"{uploaded_file.name}",
        value=default_short_description,
        key="file_desc"
    )

if uploaded_file and st.button("Save Metadata", type="primary"):
    if not uploaded_by:
        st.warning("⚠️ Please provide an 'Uploaded By' value.")
    else:
        database = "IITJ"
        schema = "MH"
        table_name = "UPLOADED_FILES_METADATA"

        # Create or replace table
        create_table_sql = f"""
        CREATE OR REPLACE TABLE {database}.{schema}.{table_name} (
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
        session.sql(create_table_sql).collect()

        def escape_sql(value: str) -> str:
            return value.replace("'", "''") if value else ""

        file_name = uploaded_file.name
        file_type = uploaded_file.type or os.path.splitext(file_name)[1].lstrip(".")
        file_size = uploaded_file.size

        insert_sql = f"""
        INSERT INTO {database}.{schema}.{table_name}
        (FILE_NAME, SHORT_DESCRIPTION, SOURCE_URL, FILE_TYPE, FILE_SIZE, UPLOADED_BY)
        VALUES ('{escape_sql(file_name)}', '{escape_sql(short_description)}',
                '{escape_sql(source_url)}', '{escape_sql(file_type)}', {file_size}, '{escape_sql(uploaded_by)}')
        """
        session.sql(insert_sql).collect()

        try:
            # Determine final filename based on compression setting
            if auto_compress:
                stage_file_name = file_name if file_name.lower().endswith(".gz") else f"{file_name}.gz"
            else:
                stage_file_name = file_name
            
            stage_path = f"@{database}.{schema}.IITJ_INFO_STAGE/{stage_file_name}"
            
            # Upload file to stage
            file_bytes = uploaded_file.getvalue()
            file_stream = io.BytesIO(file_bytes)
            
            session.file.put_stream(
                file_stream,
                stage_path,
                overwrite=True,
                auto_compress=auto_compress
            )
            
            st.success(
                f"✅ Saved metadata for '{file_name}' into {database}.{schema}.{table_name}. "
                f"Uploaded to {database}.{schema}.IITJ_INFO_STAGE."
            )
        except Exception as exc:
            st.warning(f"⚠️ Metadata saved but failed to upload {file_name} to stage: {exc}")

st.divider()
st.caption("Curate Information: Upload file metadata to Snowflake")

footer = """<style>
.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
background-color: #2C1E5B;
color: white;
text-align: center;
}
</style>
<div class="footer">
<p>Developed with ❤️ by <a style='display: inline; text-align: center;' href="https://bit.ly/atozaboutdata" target="_blank">MAHANTESH HIREMATH</a></p>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)
