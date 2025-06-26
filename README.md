# Data Extraction Tool

This is a full-stack application for extracting data from various sources. The backend is built with Python and FastAPI, and the frontend is a Next.js application.

## Technologies Used

### Backend

- Python
- FastAPI
- Pandas
- Agno
- Pytest

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- Genkit

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/Data-Extraction-Tool---Agno.git
   ```

2. **Backend Setup:**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**

   ```bash
   # Run the setup script to configure environment variables
   ./setup-env.sh
   
   # Or manually copy the shared config:
   cp .env.shared backend/.env
   cp .env.shared frontend/.env.local
   ```

   **Important:** Edit `.env.shared` with your Google API key:
   ```bash
   GOOGLE_API_KEY=your_actual_google_api_key_here
   ```

4. **Frontend Setup:**

   ```bash
   cd frontend
   npm install
   ```

### Running the Application

1. **Start the backend server:**

   ```bash
   ./start.sh
   ```

2. **Start the frontend development server:**

   ```bash
   cd frontend
   npm run dev
   ```

## Available Scripts

### Frontend

- `npm run dev`: Starts the development server.
- `npm run build`: Builds the application for production.
- `npm run start`: Starts a production server.
- `npm run lint`: Lints the code.
- `npm run typecheck`: Type-checks the code.

## Project Structure

```
.
├── backend
│   ├── app
│   ├── storage
│   └── ...
├── frontend
│   ├── src
│   └── ...
├── .gitignore
├── LICENSE
├── README.md
└── start.sh
```

<!-- README.md -->

# Data Extraction Tool

This is a full-stack application for extracting data from various sources. The backend is built with Python and FastAPI, and the frontend is a Next.js application.

## Agent Systems

This application utilizes two distinct agent systems for handling different aspects of the data extraction process:

1.  **Prompt Engineer Agent**: Responsible for generating configurations for data extraction.
2.  **Transform Data Agents**: A team of agents that work together to process and transform data.

### When to Use Each System

*   **Prompt Engineer Agent**: Use this agent when you need to create a new data extraction configuration. This agent takes a user's intent and generates a JSON schema, system and user prompts, and few-shot examples.

*   **Transform Data Agents**: Use this system when you need to process a large volume of documents or perform complex data transformations. This system is composed of four agents that work in a sequence:

    *   **Strategist**: Creates a plan for the other agents to follow.
    *   **Search**: Gathers information from the provided documents.
    *   **Codegen**: Writes Python code to perform the data extraction.
    *   **QA**: Verifies the extracted data and ensures its quality.

### Agent Prompt Examples

**Prompt Engineer Agent**

*   `Create a schema for extracting invoice data.`
*   `Generate a configuration for parsing financial reports.`
*   `I need to extract information from emails. Can you create a suitable configuration?`

**Transform Data Agents**

*   `Extract all invoice data from the uploaded documents.`
*   `Process the financial reports and save the extracted data to a CSV file.`
*   `Analyze the emails and extract the sender, recipient, and subject.`

### Architecture Decision

The decision to use two separate agent systems was made to separate the concerns of configuration generation and data processing. This allows for a more modular and maintainable architecture. The Prompt Engineer Agent is a single, specialized agent that is optimized for its specific task. The Transform Data Agents, on the other hand, are a team of agents that can be orchestrated to perform complex, multi-step data processing tasks.

This separation of concerns also allows for greater flexibility. For example, the Prompt Engineer Agent can be easily replaced with a different implementation without affecting the Transform Data Agents. Similarly, the Transform Data Agents can be customized or extended to support new data sources or transformation requirements.
