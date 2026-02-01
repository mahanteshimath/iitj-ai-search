import streamlit as st
from htbuilder.units import rem
from htbuilder import div, styles
from pathlib import Path
from snowflake.snowpark.context import get_active_session
from snowflake.core import Root
from snowflake.cortex import complete
import textwrap
import requests

st.set_page_config(page_title="IITJ AI Search", page_icon="✨", layout="wide")

# Sidebar logo
logo_path = Path(__file__).parent.parent / "resources" / "iitj.jpg"
if logo_path.exists():
    st.sidebar.image(str(logo_path), width='stretch')
    st.sidebar.markdown("---")

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

root = Root(session)

# Validate connection
with st.sidebar:
    try:
        version = session.sql("SELECT CURRENT_VERSION()").collect()[0][0]
        st.success(f"✅ Successfully connected to Database")
    except Exception as exc:
        st.error(f"Snowflake connection failed: {exc}")
        st.stop()

DB = "IITJ"
SCHEMA = "MH"
SEARCH_SERVICE = "IITJ_AI_SEARCH"
HISTORY_LENGTH = 5
FEEDBACK_TABLE = "IITJ_RAG_FFEDBACK"
LLM_MODELS = [
    "claude-3-5-sonnet",
    "llama3-70b",
    "claude-4-sonnet"
]

INSTRUCTIONS = textwrap.dedent("""
    - You are an expert chat assistance that extracts information from the CONTEXT provided.                         
    - You are a helpful AI assistant focused on answering questions about IIT Jodhpur.
    - You will be given search results from IIT Jodhpur documents as context inside <search_results> tags.
    - Use the context and conversation history to provide accurate, coherent answers.
    - Use markdown formatting: headers (starting with ##), code blocks, bullet points, and backticks for inline code.
    - Don't start responses with a markdown header.
    - Be brief but clear and informative.
    - Provide specific details from the search results.
    - If the search results don't contain relevant information, say so clearly.
    - Include source links at the end when available.
    - Don't say things like "according to the provided context" or "based on the search results".
""")

# Define helper functions early (before they're used in sidebar)
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
        return str(value)
    # Handle escaped newlines and special characters from API responses
    text = (
        value.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')  # Handle escaped quotes
        .replace("\\'", "'")   # Handle escaped single quotes
    )
    # Remove leading/trailing quotes if they wrap the entire response
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    return text

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

def ensure_feedback_table():
    session.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {DB}.{SCHEMA}.{FEEDBACK_TABLE} (
            FEEDBACK_ID NUMBER AUTOINCREMENT,
            HISTORY_OF_CHAT VARCHAR,
            MORE_INFORMATION VARCHAR,
            FEEDBACK_GIVEN_ON TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
    ).collect()

ensure_feedback_table()

SUGGESTIONS = {
    ":blue[:material/local_library:] List all faculty": "List all faculty",
    ":green[:material/school:] Departments": "Show departments at IIT Jodhpur",
    ":orange[:material/description:] Admission info": "Admission information and deadlines",
    ":violet[:material/science:] Research areas": "Research areas in AI and Data Science",
    ":red[:material/contacts:] Contact details": "Contact details for IIT Jodhpur",
}

# st.html(div(style=styles(font_size=rem(5), line_height=1))[["❉"]])

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

st.caption("This is a smart way to Search IIT Jodhpur documents uploaded by users")

st.sidebar.title("Select Models")
selected_model = st.sidebar.selectbox("Model", LLM_MODELS, index=0)

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
    limit = st.slider("Results", min_value=15, max_value=20, value=15)
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
            value="CHUNK, SOURCE_URL, TITLE, UPLOAD_TIMESTAMP",
            help="Use column names available in the search service."
        )
    
    # Debug section
    with st.expander("🔍 Debug Info", expanded=False):
        if "last_search_results" in st.session_state and st.session_state.last_search_results:
            results = st.session_state.last_search_results
            st.write(f"**Total Results:** {len(results)} chunks retrieved")
            
            for idx, row in enumerate(results, start=1):
                row_dict = normalize_row(row)
                st.write(f"**Chunk {idx}:**")
                
                # TITLE - comes from FILE_NAME alias in Cortex Search Service
                title = row_dict.get("TITLE") or row_dict.get("title") or "N/A"
                st.write(f"- Title: {title}")
                
                # SOURCE_URL - distinct source from UPLOADED_FILES_CHUNKS_TABLE
                source_url = row_dict.get("SOURCE_URL") or row_dict.get("source_url") or "N/A"
                st.write(f"- Source: {source_url}")
                
                # CHUNK - actual content
                chunk = row_dict.get("CHUNK") or row_dict.get("chunk")
                if chunk:
                    snippet = clean_text(chunk)
                    if len(snippet) > 150:
                        st.text(snippet[:150] + "...")
                    else:
                        st.text(snippet)
                
                # UPLOADED_BY
                uploaded_by = row_dict.get("UPLOADED_BY") or row_dict.get("uploaded_by")
                if uploaded_by:
                    st.write(f"- Uploaded by: {uploaded_by}")
                
                # CHUNK_INDEX
                chunk_index = row_dict.get("CHUNK_INDEX") or row_dict.get("chunk_index")
                if chunk_index:
                    st.write(f"- Chunk Index: {chunk_index}")
                
                st.markdown("---")
        else:
            st.write("No search performed yet.")
        
        if "last_search_context" in st.session_state:
            st.write("**Search Context Used:**")
            context = st.session_state.last_search_context
            if len(context) > 500:
                st.text(context[:500] + "...")
            else:
                st.text(context)

def build_search_context(results: list[dict]) -> str:
    """Build context string from search results for LLM prompt."""
    if not results:
        return "No relevant documents found."

    context_blocks = []
    for idx, row in enumerate(results, start=1):
        row_dict = normalize_row(row)
        title = clean_text(row_dict.get("TITLE") or row_dict.get("FILE_NAME") or f"Document {idx}")
        source_url = row_dict.get("SOURCE_URL") # or row_dict.get("SOURCE")
        uploaded_by = clean_text(row_dict.get("UPLOADED_BY") or row_dict.get("UPLOADER"))
        chunk_index = row_dict.get("CHUNK_INDEX")
        snippet = clean_text(
            row_dict.get("CONTENT")
            or row_dict.get("CHUNK")
            or row_dict.get("PAGE_CHUNK")
        )

        block = f"[Document {idx} - {title}]"
        if uploaded_by:
            block += f"\nUploaded by: {uploaded_by}"
        if chunk_index is not None:
            block += f"\nChunk index: {chunk_index}"
        if snippet:
            block += f"\n{snippet}"
        if source_url:
            block += f"\nSource: {source_url}"

        context_blocks.append(block)

    return "\n\n".join(context_blocks)

def history_to_text(chat_history):
    """Converts chat history into a string."""
    return "\n".join(f"[{h['role']}]: {h['content']}" for h in chat_history)

def build_prompt(question: str, search_context: str, recent_history: str = None) -> str:
    """Build the complete prompt for the LLM."""
    prompt_parts = [f"<instructions>\n{INSTRUCTIONS}\n</instructions>"]
    
    if search_context:
        prompt_parts.append(f"<search_results>\n{search_context}\n</search_results>")
    
    if recent_history:
        prompt_parts.append(f"<recent_conversation>\n{recent_history}\n</recent_conversation>")
    
    prompt_parts.append(f"<question>\n{question}\n</question>")
    
    return "\n\n".join(prompt_parts)

def get_response(prompt: str, model: str):
    """Get streaming response from LLM using SQL-based Cortex COMPLETE."""
    try:
        # Use SQL-based COMPLETE function for better compatibility
        response = session.sql(
            "SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(?, ?) as response",
            params=[model, prompt]
        ).collect()
        
        if response and len(response) > 0:
            raw_response = response[0]['RESPONSE']
            # Clean escape sequences and convert to proper formatting
            cleaned_response = clean_text(raw_response)
            return cleaned_response
        else:
            st.error("No response received from the model.")
            st.stop()
            
    except Exception as exc:
        error_msg = f"Model request failed: {type(exc).__name__}\n{str(exc)}"
        st.error(
            f"{error_msg}\n\n"
            f"Model: `{model}`\n\n"
            f"💡 Try selecting a different model from the sidebar.\n"
            f"Common models: mistral-large, llama3-70b, mixtral-8x7b\n\n"
            f"Make sure Cortex AI is enabled in your Snowflake account."
        )
        st.stop()

def show_feedback_controls(message_index):
    """Shows the 'How did I do?' control."""
    st.write("")

    with st.popover("How did I do?"):
        with st.form(key=f"feedback-{message_index}", border=False):
            with st.container(gap=None):
                st.markdown(":small[Rating]")
                rating = st.feedback(options="stars")

            details = st.text_area("More information (optional)")

            if st.checkbox("Include chat history with my feedback", True):
                relevant_history = st.session_state.messages
            else:
                relevant_history = []

            ""  # Add some space

            if st.form_submit_button("Send feedback"):
                history_text = history_to_text(relevant_history) if relevant_history else None
                try:
                    session.sql(
                        f"""
                        INSERT INTO {DB}.{SCHEMA}.{FEEDBACK_TABLE}
                        (HISTORY_OF_CHAT, MORE_INFORMATION)
                        SELECT ?, ?
                        """,
                        params=[history_text, details],
                    ).collect()
                    st.success("Thank you for your feedback!")
                except Exception as exc:
                    st.error(f"Failed to store feedback: {exc}")

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

def clear_conversation():
    st.session_state.messages = []
    st.session_state.initial_question = None
    st.session_state.selected_suggestion = None

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.container()  # Fix ghost message bug
        
        st.markdown(message["content"])
        
        if message["role"] == "assistant":
            show_feedback_controls(i)

if user_message:
    # Escape LaTeX characters
    user_message = user_message.replace("$", r"\$")
    
    with st.chat_message("user"):
        st.text(user_message)

    with st.chat_message("assistant"):
        # Search for relevant context
        with st.spinner("Searching documents..."):
            try:
                results = run_search(user_message)
                st.session_state.last_search_results = results  # Store for debug
                search_context = build_search_context(results)
                st.session_state.last_search_context = search_context  # Store context for debug
                
                # Extract all unique source URLs from results (keep as raw values)
                source_urls = []
                for row in results:
                    row_dict = normalize_row(row)
                    url = row_dict.get("SOURCE_URL") or row_dict.get("SOURCE")
                    if url and url not in source_urls:
                        source_urls.append(url)
            except Exception as exc:
                search_context = f"Error searching documents: {exc}"
                source_urls = []
        
        # Build prompt with context and history
        recent_history = st.session_state.messages[-HISTORY_LENGTH:] if len(st.session_state.messages) > 0 else []
        recent_history_str = history_to_text(recent_history) if recent_history else None
        
        full_prompt = build_prompt(user_message, search_context, recent_history_str)
        
        # Get LLM response
        with st.spinner("Thinking..."):
            response = get_response(full_prompt, selected_model)
        
        # Append source URLs at the end (always show sources)
        if source_urls:
            response += "\n\n---\n"
            response += "**Source:** "
            response += source_urls[0]  # Keep raw URL
        else:
            response += "\n\n---\n"
            response += "**Source:** Not available"
        
        # Display the response and save to history
        with st.container():
            st.markdown(response)
            
            # Add to chat history
            st.session_state.messages.append({"role": "user", "content": user_message})
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Show feedback
            show_feedback_controls(len(st.session_state.messages) - 1)

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

.restart-btn {
position: fixed;
right: 1.5rem;
bottom: 3rem;
z-index: 1000;
}
</style>
<div class="footer">
<p>Developed with ❤️ by <a style='display: inline; text-align: center;' href="https://bit.ly/atozaboutdata" target="_blank">MAHANTESH HIREMATH</a></p>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="restart-btn">', unsafe_allow_html=True)
    _, _, _, right_col = st.columns([6, 1, 1, 1])
    with right_col:
        st.button(
            "Restart",
            icon=":material/refresh:",
            on_click=clear_conversation,
        )
    st.markdown('</div>', unsafe_allow_html=True)
