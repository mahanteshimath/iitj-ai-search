import streamlit as st
from htbuilder.units import rem
from htbuilder import div, styles
from snowflake.snowpark.context import get_active_session
from snowflake.core import Root

st.set_page_config(page_title="IITJ AI Search", page_icon="✨", layout="wide")

st.markdown(
    '''
    <style>
    .streamlit-expanderHeader {
        background-color: #2C1E5B;
        color: white;
    }
    .streamlit-expanderContent {
        background-color: #0E0B1F;
        color: white;
    }
    </style>
    ''',
    unsafe_allow_html=True
)

# Connect to Snowflake
try:
    session = get_active_session()
except Exception:
    from snowflake.snowpark import Session
    session = Session.builder.configs(st.secrets["connections"]["snowflake"]).create()

root = Root(session)

DB = "IITJ"
SCHEMA = "MH"
SEARCH_SERVICE = "IITJ_AI_SEARCH"

def get_indexed_columns() -> list[str]:
    try:
        rows = session.sql(
            f"DESCRIBE CORTEX SEARCH SERVICE {DB}.{SCHEMA}.{SEARCH_SERVICE}"
        ).collect()
    except Exception:
        return []

    for row in rows:
        row_dict = row.as_dict() if hasattr(row, "as_dict") else dict(row)
        name = (row_dict.get("name") or row_dict.get("NAME") or "").lower()
        if name in {"columns", "search_columns", "indexed_columns"}:
            value = row_dict.get("value") or row_dict.get("VALUE") or ""
            return [c.strip() for c in value.split(",") if c.strip()]
    return []

indexed_columns = get_indexed_columns()

SUGGESTIONS = {
    ":blue[:material/local_library:] List all faculty": "List all faculty",
    ":green[:material/school:] Departments": "Show departments at IIT Jodhpur",
    ":orange[:material/description:] Admission info": "Admission information and deadlines",
    ":violet[:material/science:] Research areas": "Research areas in AI and Data Science",
    ":red[:material/contacts:] Contact details": "Contact details for IIT Jodhpur",
}

st.html(div(style=styles(font_size=rem(5), line_height=1))[["❉"]])

title_row = st.container(
    horizontal=True,
    vertical_alignment="bottom",
)

with title_row:
    st.title(
        "IITJ AI Search",
        anchor=False,
        width="stretch",
    )

st.caption("Search IIT Jodhpur documents uploaded by users using a Cortex Search Service")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "initial_question" not in st.session_state:
    st.session_state.initial_question = None

if "selected_suggestion" not in st.session_state:
    st.session_state.selected_suggestion = None

user_just_asked_initial_question = (
    "initial_question" in st.session_state and st.session_state.initial_question
)

user_just_clicked_suggestion = (
    "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
)

user_first_interaction = (
    user_just_asked_initial_question or user_just_clicked_suggestion
)

has_message_history = len(st.session_state.messages) > 0

with st.sidebar:
    st.subheader("Search settings")
    limit = st.slider("Results", min_value=1, max_value=20, value=5)
    if indexed_columns:
        selected_columns = st.multiselect(
            "Columns",
            options=indexed_columns,
            default=indexed_columns[:3],
            help="These are the indexed columns for this search service."
        )
    else:
        selected_columns = []
        columns = st.text_input(
            "Columns (comma-separated)",
            value="CONTENT,SOURCE_URL,TITLE,UPLOAD_TIMESTAMP",
            help="Use column names available in the search service."
        )

def parse_columns(raw: str) -> list[str]:
    return [c.strip() for c in raw.split(",") if c.strip()]

def normalize_row(row) -> dict:
    if isinstance(row, dict):
        return row
    if hasattr(row, "as_dict"):
        return row.as_dict()
    return dict(row)

def clean_text(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    return (
        value.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
    )

def format_results(results: list[dict]) -> str:
    if not results:
        return "No results found."

    blocks = []
    for idx, row in enumerate(results, start=1):
        row_dict = normalize_row(row)
        title = clean_text(row_dict.get("TITLE") or row_dict.get("FILE_NAME") or f"Result {idx}")
        source_url = clean_text(row_dict.get("SOURCE_URL") or row_dict.get("SOURCE"))
        snippet = clean_text(
            row_dict.get("CONTENT")
            or row_dict.get("CHUNK")
            or row_dict.get("PAGE_CHUNK")
        )

        block_lines = [f"### {title}"]
        if snippet:
            block_lines.append(snippet)

        extras = {
            k: v
            for k, v in row_dict.items()
            if k not in {"TITLE", "FILE_NAME", "SOURCE_URL", "SOURCE", "CONTENT", "CHUNK", "PAGE_CHUNK"}
        }
        if extras:
            for key, value in extras.items():
                block_lines.append(f"- **{key}**: {clean_text(value)}")

        if source_url:
            block_lines.append("Related links:")
            block_lines.append(f"- [Source]({source_url})")

        blocks.append("\n\n".join(block_lines))

    return "\n\n---\n\n".join(blocks)

def run_search(question: str) -> list[dict]:
    cortex_search_service = (
        root.databases[DB].schemas[SCHEMA].cortex_search_services[SEARCH_SERVICE]
    )
    if indexed_columns:
        cols = selected_columns or indexed_columns
        return cortex_search_service.search(
            question,
            columns=cols,
            filter={},
            limit=limit,
        ).results

    cols = parse_columns(columns) if "columns" in locals() else []
    if cols:
        return cortex_search_service.search(
            question,
            columns=cols,
            filter={},
            limit=limit,
        ).results

    return cortex_search_service.search(
        question,
        filter={},
        limit=limit,
    ).results

if not user_first_interaction and not has_message_history:
    with st.container():
        st.chat_input("Ask a question...", key="initial_question")

        selected_suggestion = st.pills(
            label="Examples",
            label_visibility="collapsed",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
        )

    st.stop()

user_message = st.chat_input("Ask a follow-up...")

if not user_message:
    if user_just_asked_initial_question:
        user_message = st.session_state.initial_question
    if user_just_clicked_suggestion:
        user_message = SUGGESTIONS[st.session_state.selected_suggestion]

with title_row:

    def clear_conversation():
        st.session_state.messages = []
        st.session_state.initial_question = None
        st.session_state.selected_suggestion = None

    st.button(
        "Restart",
        icon=":material/refresh:",
        on_click=clear_conversation,
    )

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_message:
    with st.chat_message("user"):
        st.text(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            try:
                results = run_search(user_message)
                response = format_results(results)
            except Exception as exc:
                response = f"Search failed: {exc}"

        st.markdown(response)

        st.session_state.messages.append({"role": "user", "content": user_message})
        st.session_state.messages.append({"role": "assistant", "content": response})

footer="""<style>

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
