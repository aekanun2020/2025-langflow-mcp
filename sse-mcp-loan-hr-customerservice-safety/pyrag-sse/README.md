# RAG MCP Server with SSE Transport

A Model Context Protocol (MCP) server for RAG (Retrieval-Augmented Generation) documentation system with SSE (Server-Sent Events) transport, containerized with Docker.

## Features

- **SSE Transport**: Real-time communication using Server-Sent Events
- **Vector Database Integration**: Uses Qdrant for semantic search
- **Document Processing**: Support for PDF and text files
- **Embedding Support**: Ollama and OpenAI embeddings
- **FastAPI Backend**: Modern, fast web framework
- **Docker Support**: Fully containerized application with docker-compose
- **MCP Tools**: 
  - Add documentation from URLs
  - Search stored documentation
  - List documentation sources
  - Add entire directories
- **MCP Resources**:
  - List all documentation sources
  - Get database statistics
- **MCP Prompts**:
  - Search templates
  - Documentation analysis

## Architecture

Based on the successful SSE-MSSQLMCP pattern, this project provides:
- SSE endpoint for real-time MCP communication
- Message endpoint for handling MCP requests
- Integration with Qdrant vector database
- Support for multiple embedding providers

## Quick Start

### Using Docker Compose

1. Clone the repository and navigate to the project directory

2. Create `.env` file from example:
```bash
cp .env.example .env
```

3. Start the services:
```bash
docker-compose up
```

This will start:
- Qdrant vector database on port 6333
- PyRAGDoc SSE server on port 9000

## API Endpoints

- `GET /sse` - SSE connection endpoint for MCP
- `POST /messages` - Message handling endpoint
- `GET /health` - Health check endpoint
- `GET /` - API documentation

**Note:** When using Docker, the server runs internally on port 8000 but is exposed externally on port 9000.

## License

MIT

## Credits

Based on the SSE-MSSQLMCP pattern for MCP server implementation with SSE transport.
