# MSSQL MCP Server with SSE Transport

A Model Context Protocol (MCP) server that provides SQL Server database access through SSE (Server-Sent Events) transport, containerized with Docker.

## Features

- **SSE Transport**: Real-time communication using Server-Sent Events
- **MSSQL Integration**: Connect to Microsoft SQL Server databases
- **FastAPI Backend**: Modern, fast web framework
- **Docker Support**: Fully containerized application
- **MCP Tools**: 
  - Execute SQL queries
  - Preview tables
  - Get database information
  - Refresh schema cache
- **MCP Resources**:
  - List all tables
  - Get table schemas
- **MCP Prompts**:
  - Data analysis templates
  - SQL query generation

## Quick Start

### 1. Edit a `.env` file with your database configuration:

```env
DB_SERVER=your_server_address
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

### 2. Run Docker Compose

```bash
docker-compose up
```


## API Endpoints

- `GET /sse` - SSE connection endpoint
- `POST /messages` - Message handling endpoint
- `GET /health` - Health check endpoint
- `GET /` - API documentation

**Note:** When using Docker, the server runs internally on port 8000 but is exposed externally on port 9000.

## License

MIT
