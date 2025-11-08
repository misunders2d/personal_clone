# Personal Clone: Your Unified Second Brain

Personal Clone is an AI-powered "second brain" built on Google's Agent Development Kit (ADK). It centralizes all your communications and experiences into a single, reliable knowledge base, turning your fallible memory into a structured, searchable asset.

## Core Features

- **Unified Knowledge Storage**: All interactions are vectorized and stored in Pinecone, enabling semantic search across your entire knowledge ecosystem.
- **Context-Aware Agent Orchestration**: The `PersonalClone` agent, powered by ADK, maintains persistent session state and intelligently routes queries to a suite of specialized sub-agents.
- **Modular Tools Ecosystem**: A rich set of tools for automation, including:
    - **Pinecone Tools**: For memory and knowledge management.
    - **GitHub Tools**: To enable self-evolution of the agent's codebase.
    - **ClickUp Tools**: For task and workflow automation.
    - **BigQuery Tools**: For data analysis and business intelligence.
    - **Search & Scraping Tools**: For accessing external information.
- **Self-Evolution Capabilities**: The `github_agent` allows the system to review and modify its own code, enabling it to adapt and evolve over time.
- **Multi-Channel Independence**: Deployed on Google Agent Engine, the system can connect to any communication channel, creating a unified view of all your interactions.

## Architecture

The system is designed as a multi-agent system, with a `root_agent` that orchestrates the workflow. The `root_agent` is a `SequentialAgent` that first calls an `answer_validator_agent` to determine if a response is needed, and then passes control to the `main_agent`.

The `main_agent` is the core of the system, with access to a wide range of tools and sub-agents, including:

- `memory_agent`: For interacting with the Pinecone knowledge base.
- `bigquery_agent`: For querying BigQuery datasets.
- `clickup_agent`: For managing ClickUp tasks.
- `github_agent`: For interacting with GitHub repositories.
- `google_search_agent`: For performing Google searches.
- `vertex_search_agent`: For searching Vertex AI datastores.
- `code_executor_agent`: For executing Python code.

The agent's behavior is further customized using a series of callbacks that are triggered at different points in the agent's lifecycle.

## Getting Started

### Prerequisites

- Python 3.10+
- `uv`
- An active Google Cloud project with the following APIs enabled:
    - Vertex AI API
    - BigQuery API
- API keys for:
    - Pinecone
    - ClickUp
    - GitHub

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/misunders2d/personal_clone.git
   cd personal_clone
   ```

2. **Install dependencies:**
   ```bash
   make install
   ```

3. **Configure your environment:**
   Create a `.env` file in the root of the project and add the following environment variables:
   ```
   GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
   GOOGLE_CLOUD_LOCATION="your-gcp-location"
   GOOGLE_CLOUD_STORAGE_BUCKET="your-gcs-bucket"
   VERTEX_DATASTORE_ID="your-vertex-datastore-id"
   GCP_SERVICE_ACCOUNT_INFO='your-gcp-service-account-info'
   BQ_SERVICE_ACCOUNT_INFO='your-bq-service-account-info' # if your BQ data is in a different project than your GCP
   OPENAI_API_KEY="your-openai-api-key" # if using openai models
   GROK_API_KEY="your-grok-api-key" # if using grok models
   MINIMAX_API_KEY="your-minimax-api-key" # if using minimax
   NEO4J_DATABASE="your-neo4j-database" # if using neo4j for graph dbs
   NEO4J_URI="your-neo4j-uri" # if using neo4j for graph dbs
   NEO4J_USERNAME="your-neo4j-username" # if using neo4j for graph dbs
   NEO4J_PASSWORD="your-neo4j-password" # if using neo4j for graph dbs
   CLICKUP_API_TOKEN="your-clickup-api-token"
   CLICKUP_TEAM_ID="your-clickup-team-id"
   GITHUB_TOKEN="your-github-token"
   DEFAULT_GITHUB_REPO="your-default-github-repo" # for the personal clone itself
   PINECONE_API_KEY="your-pinecone-api-key"
   PINECONE_INDEX_NAME="your-pinecone-index-name"
   SUPERUSERS="user1@example.com,user2@example.com" # for admin emails
   TEAM_DOMAIN="example.com" # used in callbacks to restrict access to corporate data
   ```

### Running the Agent

You can run the agent locally using the ADK web UI:

```bash
adk web
```

This will start a web server with a chat interface for interacting with the agent.

## Deployment

The agent is configured for deployment to Google Agent Engine. The configuration is defined in `personal_clone/.agent_engine_config.json`.

To deploy the agent, you can use the `adk deploy agent_engine` command.

## Development

The `personal-clone` agent is built with a modular and extensible architecture. To add new functionality, you can create new tools or sub-agents.

- **Tools**: Tools are defined in the `personal_clone/tools` directory. Each tool is a Python function that can be called by the agent.
- **Sub-agents**: Sub-agents are defined in the `personal_clone/sub_agents` directory. Each sub-agent is a specialized agent that can be called by the `main_agent`.

## Future Vision

The `personal-clone` project is constantly evolving. Future plans include:

- **Runtime Model Swapping**: The ability to swap LLM models at runtime.
- **Multi-modal Support**: Support for voice and video interactions.
- **Enterprise Features**: Role-based access control and other enterprise-grade features.