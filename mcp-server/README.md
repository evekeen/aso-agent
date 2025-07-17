# ASO Agent MCP Server

A Model Context Protocol (MCP) server that provides streaming ASO (App Store Optimization) analysis through your existing ASO Agent HTTP API.

## Features

- **Streaming Analysis**: Real-time progress updates during ASO analysis
- **Comprehensive ASO Metrics**: Keyword difficulty, traffic analysis, and market size data
- **Interactive Clarification**: Handles vague requests with follow-up questions
- **Multiple Analysis Modes**: Streaming and non-streaming analysis options
- **Service Health Monitoring**: Built-in health checks for the ASO service

## Installation

1. Install dependencies:
```bash
cd mcp-server
npm install
```

2. Build the TypeScript code:
```bash
npm run build
```

3. Ensure your ASO Agent service is running on `http://localhost:8080`

## Usage

### Configuration

Add this to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "aso-agent": {
      "command": "node",
      "args": ["/Users/ivkin/my/aso-agent/mcp-server/dist/index.js"],
      "env": {
        "ASO_SERVICE_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Available Tools

#### 1. `analyze-app-ideas`
Analyze app ideas for ASO opportunities with streaming support.

**Parameters:**
- `message` (required): Describe the app ideas to analyze
- `model` (optional): LLM model to use (default: "gpt-4o-mini")
- `market_threshold` (optional): Minimum market size in USD (default: 50000)
- `keywords_per_idea` (optional): Number of keywords per app idea (default: 30)
- `stream` (optional): Enable streaming updates (default: true)
- `user_id` (optional): User ID for tracking
- `thread_id` (optional): Thread ID for conversation context

**Example:**
```
analyze-app-ideas with message="fitness tracking apps for runners" and market_threshold=25000
```

#### 2. `check-aso-service`
Check if the ASO analysis service is healthy and available.

**Example:**
```
check-aso-service
```

### Available Prompts

#### 1. `aso-analysis-guide`
Comprehensive guide for ASO analysis best practices.

#### 2. `keyword-difficulty-guide`
Detailed explanation of keyword difficulty and traffic metrics.

## Streaming Features

The MCP server supports real-time streaming updates during analysis:

### Progress Updates
- **Real-time progress**: Shows progress percentage for each analysis step
- **Step-by-step updates**: Displays current analysis phase and status
- **Progress tracking**: Uses MCP's `reportProgress` for visual progress bars

### Intermediate Results
- **Keywords Generated**: Shows number of keywords generated per app idea
- **Apps Found**: Displays total apps found for keyword analysis
- **Market Size Analysis**: Shows top market opportunities as they're calculated

### Interactive Clarification
- **Vague Input Handling**: Asks clarifying questions for unclear requests
- **Follow-up Questions**: Guides users toward more specific app ideas
- **Conversation Context**: Maintains thread context across interactions

## Example Analysis Flow

1. **Input**: "meditation apps"
2. **Clarification**: "What specific type of meditation apps? For anxiety relief, sleep, or general mindfulness?"
3. **Refined Input**: "meditation apps for anxiety relief"
4. **Streaming Analysis**:
   - 📊 Collecting App Ideas - Analyzing user message (25%)
   - 📝 Keywords Generated: 30 keywords across 1 app ideas
   - 📱 Apps Found: 245 apps found for keyword analysis
   - 💰 Market Size Analysis: Top opportunities calculated
   - 🎯 Final Results: Top performing keywords identified

## Service Integration

The MCP server communicates with your ASO Agent service via HTTP:

- **Health Checks**: Verifies service availability before analysis
- **Streaming API**: Uses Server-Sent Events for real-time updates
- **Error Handling**: Graceful error handling with informative messages
- **Configuration**: Supports all ASO Agent configuration options

## Development

### Running in Development Mode

```bash
npm run dev  # Watches for TypeScript changes
```

### Building for Production

```bash
npm run build
npm run start
```

### Testing

Ensure your ASO Agent service is running, then test the MCP server:

```bash
# Check service health
echo '{"method": "tools/call", "params": {"name": "check-aso-service", "arguments": {}}}' | node dist/index.js

# Test analysis
echo '{"method": "tools/call", "params": {"name": "analyze-app-ideas", "arguments": {"message": "fitness apps", "stream": false}}}' | node dist/index.js
```

## Architecture

```
Claude Desktop (MCP Client)
    ↓
ASO Agent MCP Server (TypeScript)
    ↓ HTTP API
ASO Agent Service (FastAPI)
    ↓
LangGraph ASO Analysis Pipeline
```

## Troubleshooting

### Service Not Available
- Ensure ASO Agent service is running on port 8080
- Check service health with `check-aso-service` tool
- Verify network connectivity

### Streaming Issues
- Confirm streaming is enabled in tool parameters
- Check that the service supports Server-Sent Events
- Monitor console output for streaming errors

### Configuration Issues
- Verify MCP client configuration is correct
- Check that the server path is absolute
- Ensure all required environment variables are set

## Contributing

1. Follow the existing TypeScript patterns
2. Add proper error handling for all API calls
3. Include streaming support for long-running operations
4. Document any new tools or prompts
5. Test with the actual ASO Agent service

## License

ISC