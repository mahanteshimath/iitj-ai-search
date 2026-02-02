# IITJ AI Search

A Streamlit-based application for curating and searching IITJ (Indian Institute of Technology Jodhpur) information using AI-powered search capabilities.

## Overview

This application provides an intelligent document management and search system that allows users to:
- Upload documents to Snowflake cloud storage
- Automatically generate embeddings for semantic search
- Search through uploaded documents using AI with Cortex Search
- Export chat history as PDF
- Manage document metadata and access control

## Features

### 📋 Document Curation
- **Secure Upload**: User authentication system for document uploads
- **Metadata Management**: Track file names, descriptions, source URLs, file types, and uploaders
- **Cloud Storage**: Documents stored in Snowflake stages with encryption
- **Automatic Embeddings**: AI-powered embeddings generated for uploaded documents
- **File Filtering**: Search and filter uploaded files by name, uploader, or source URL

### 🔍 AI Search
- **Semantic Search**: Cortex Search-powered semantic search across documents
- **LLM-Powered Answers**: Claude 3.5 Sonnet and Claude 4 Sonnet models for intelligent responses
- **Context-Aware**: Maintains conversation history for follow-up questions
- **Source Attribution**: Automatic source linking to original documents
- **Customizable Results**: Adjustable search result limits (10-20)
- **Quick Examples**: Pre-configured suggestion prompts for common queries

### 💾 Export Features
- **PDF Export**: Save chat history as formatted PDF with timestamp
- **Conversation Management**: Clear and restart conversations
- **Feedback System**: Rating and feedback collection for responses

### 🔐 Authentication
- Secure login system using Snowflake-based authentication
- User-specific upload tracking
- Email-based access control

## Technology Stack

- **Frontend**: Streamlit
- **Backend**: Snowflake (Data Warehouse & Cortex AI)
- **Language**: Python 3.8+
- **Storage**: Snowflake Stages with SSE encryption
- **AI/ML**: 
  - Snowflake Cortex Search for semantic search
  - Claude 3.5 Sonnet / Claude 4 Sonnet for LLM responses
  - Automatic embedding generation
- **PDF Generation**: ReportLab

## Project Structure

```
.
├── Home.py                          # Main application entry point
├── pages/
│   ├── 01_Curate_Information.py    # Document upload and management
│   └── 02_AI_Search.py             # AI-powered search interface with chat
├── resources/
│   └── iitj.jpg                    # IITJ logo
├── .streamlit/
│   ├── config.toml                 # Streamlit configuration
│   └── secrets.toml                # Snowflake credentials (not in git)
├── requirements.txt                 # Python dependencies
└── README.md
```

## Prerequisites

- Python 3.8+
- Snowflake account with:
  - Cortex AI enabled
  - Appropriate permissions for stages, tables, and Cortex Search
- IITJ email credentials for document upload access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/iitj-ai-search.git
cd iitj-ai-search
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Snowflake connection in `.streamlit/secrets.toml`:
```toml
[connections.snowflake]
account = "your_account"
user = "your_user"
password = "your_password"
role = "your_role"
warehouse = "your_warehouse"
database = "IITJ"
schema = "MH"
```

## Usage

1. Start the application:
```bash
streamlit run Home.py
```

2. **Curate Information** (Page 1):
   - Login with your IITJ credentials
   - Upload documents (PDF, DOCX, TXT, etc.) with descriptions and source URLs
   - View uploaded files metadata with filtering options
   - Track upload timestamps and file information

3. **AI Search** (Page 2):
   - Ask questions about IITJ using natural language
   - Get AI-powered answers with source citations
   - Use example prompts or ask custom queries
   - Adjust search settings (result limit, model selection)
   - Save chat history as PDF
   - Provide feedback on responses

## Database Schema

### Tables
- **UPLOADED_FILES_METADATA**: Stores document metadata (file name, description, source URL, uploader, timestamp, etc.)
- **IITJ_DOCUMENT_CURATOR_INFO**: User authentication data
- **IITJ_RAG_FEEDBACK**: Stores user feedback and ratings for AI responses

### Snowflake Objects
- **Stage**: `IITJ.MH.IITJ_INFO_STAGE` (encrypted storage for uploaded documents)
- **Cortex Search Service**: `IITJ.MH.IITJ_AI_SEARCH` (semantic search service)
- **Procedure**: `GENERATE_EMBEDDINGS_FOR_NEW_FILE` (automatic embedding generation)

## Features in Detail

### Document Upload Flow
1. User authentication verification
2. File upload to Snowflake stage with encryption
3. Metadata insertion into database
4. Automatic embedding generation via stored procedure
5. Integration with Cortex Search service

### AI Search Capabilities
- **Semantic Search**: Uses Cortex Search to find relevant document chunks
- **LLM Integration**: Multiple model options (Claude 3.5 Sonnet, Claude 4 Sonnet)
- **Context Building**: Combines search results with conversation history
- **Response Formatting**: Markdown-formatted responses with source links
- **Debug Mode**: View search results, context, and distinct documents
- **Chat History**: Maintains last 5 interactions for context

### PDF Export
- Formatted chat history with color-coded roles
- Timestamp and metadata
- Proper pagination and layout
- Automatic filename with timestamp

## Security

- Snowflake SSE encryption for staged files
- Password-protected user authentication
- Session-based access control
- Secure credential management via Streamlit secrets
- Row-level security for uploaded documents

## Available Models

- **claude-3-5-sonnet** (default): Advanced reasoning and detailed responses
- **claude-4-sonnet**: Latest Claude model with enhanced capabilities

## Troubleshooting

### Connection Issues
- Verify Snowflake credentials in `.streamlit/secrets.toml`
- Ensure Cortex AI is enabled in your Snowflake account
- Check warehouse status and permissions

### Search Not Working
- Verify Cortex Search service is created: `IITJ.MH.IITJ_AI_SEARCH`
- Ensure documents have been uploaded and embeddings generated
- Check indexed columns configuration

### PDF Export Issues
- Ensure `reportlab` is installed: `pip install reportlab`
- Check for long messages that might cause formatting issues

## Development

### Key Components

- **Session Management**: Automatic reconnection and session state persistence
- **Error Handling**: Comprehensive error messages for troubleshooting
- **Responsive UI**: Mobile-friendly design with IITJ branding
- **Modular Code**: Separate functions for search, LLM, and context building

## Credits

Developed with ❤️ by **Mahantesh Hiremath** (M25AI2134@IITJ.AC.IN)

## License

[Add your license information here] 
