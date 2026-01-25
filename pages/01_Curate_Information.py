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

col1, col2 = st.columns(2)
with col1:
    uploaded_by = st.text_input("Uploaded By", placeholder="Your name or email")
with col2:
    source_url = st.text_input("Source URL", placeholder="https://...")

default_short_description = st.text_input(
    "Default Short Description",
    placeholder="Optional default description for all files"
)

st.subheader("📁 Upload Files")
uploaded_files = st.file_uploader(
    "Choose file(s)",
    type=None,
    accept_multiple_files=True
)

short_descriptions = {}
if uploaded_files:
    st.markdown("### 📝 Per-File Short Description")
    for uploaded_file in uploaded_files:
        short_descriptions[uploaded_file.name] = st.text_input(
            f"{uploaded_file.name}",
            value=default_short_description
        )

if uploaded_files and st.button("Save Metadata", type="primary"):
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

        inserted = 0
        uploaded_to_stage = 0
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            file_type = uploaded_file.type or os.path.splitext(file_name)[1].lstrip(".")
            file_size = uploaded_file.size
            short_description = short_descriptions.get(file_name, default_short_description)

            insert_sql = f"""
            INSERT INTO {database}.{schema}.{table_name}
            (FILE_NAME, SHORT_DESCRIPTION, SOURCE_URL, FILE_TYPE, FILE_SIZE, UPLOADED_BY)
            VALUES ('{escape_sql(file_name)}', '{escape_sql(short_description)}',
                    '{escape_sql(source_url)}', '{escape_sql(file_type)}', {file_size}, '{escape_sql(uploaded_by)}')
            """
            session.sql(insert_sql).collect()
            inserted += 1

            try:
                stage_file_name = file_name if file_name.lower().endswith(".gz") else f"{file_name}.gz"
                stage_path = f"@{database}.{schema}.IITJ_INFO_STAGE/{stage_file_name}"
                session.file.put_stream(
                    io.BytesIO(uploaded_file.getvalue()),
                    stage_path,
                    overwrite=True
                )
                uploaded_to_stage += 1
            except Exception as exc:
                st.warning(f"⚠️ Metadata saved but failed to upload {file_name} to stage: {exc}")

        st.success(
            f"✅ Saved metadata for {inserted} file(s) into {database}.{schema}.{table_name}. "
            f"Uploaded {uploaded_to_stage} file(s) to {database}.{schema}.IITJ_INFO_STAGE."
        )

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
