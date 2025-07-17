import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerASOTools } from "./aso-tools.js";

const server = new McpServer({
  name: "aso-agent",
  version: "1.0.0",
  capabilities: {
    resources: {},
    tools: {},
    prompts: {}
  }
});

// Register ASO analysis tools
registerASOTools(server);

// Add prompts for guidance
server.registerPrompt(
  "aso-analysis-guide",
  {
    title: "ASO Analysis Guide",
    description: "Guide for analyzing app ideas for ASO opportunities"
  },
  async () => ({
    messages: [
      {
        role: "user",
        content: {
          type: "text",
          text: `You are an expert in App Store Optimization (ASO) analysis. When analyzing app ideas, follow these guidelines:

## ASO Analysis Best Practices

### 1. App Idea Specification
- Be specific about the app category and target audience
- Examples of good requests:
  - "Analyze fitness tracking apps for runners"
  - "Explore meditation apps for anxiety relief"
  - "Research productivity tools for remote workers"

### 2. Keyword Analysis Criteria
- **Top Performers**: Traffic ≥ 200, Difficulty < 3.0, Market Size ≥ threshold
- **Good Keywords**: Traffic ≥ 100, Difficulty < 4.0, Market Size ≥ 50% of threshold
- **Avoid**: Keywords with 0.0 difficulty (too weak) or difficulty ≥ 4.0 (too hard)

### 3. Market Size Interpretation
- Market size represents monthly revenue potential in USD
- Higher market size = more revenue opportunity
- Don't sum market sizes across keywords (they're separate opportunities)

### 4. Opportunity Assessment
- Focus on keywords with high traffic/difficulty ratio
- Consider market size relative to your threshold
- Look for keywords with reasonable difficulty levels

### 5. Streaming Analysis
- Use streaming mode for real-time progress updates
- Monitor intermediate results during analysis
- Get immediate feedback on each analysis step

Use the analyze-app-ideas tool to get comprehensive ASO analysis for any app concept.`
        }
      }
    ]
  })
);

server.registerPrompt(
  "keyword-difficulty-guide",
  {
    title: "Keyword Difficulty Interpretation",
    description: "How to interpret keyword difficulty and traffic metrics"
  },
  async () => ({
    messages: [
      {
        role: "user",
        content: {
          type: "text",
          text: `Understanding ASO Keyword Metrics:

## Difficulty Scale (0-10)
- **0.0-2.9**: Easy to rank (Top Performers)
- **3.0-3.9**: Moderate difficulty (Good opportunity)
- **4.0+**: Hard to rank (Avoid unless huge market)
- **0.0**: No data available (Weak keywords)

## Traffic Scale (0-100)
- **200+**: High traffic (Top Performers)
- **100-199**: Good traffic (Good opportunity)
- **50-99**: Moderate traffic
- **Below 50**: Low traffic potential

## Market Size (USD)
- Monthly revenue potential for that keyword
- Actual market depends on your app's capture rate
- Higher values = more revenue opportunity
- Use market threshold to filter viable keywords

## Opportunity Score
- Calculated as Traffic ÷ Difficulty
- Higher scores = better opportunities
- Considers both competition and potential

## Status Indicators
- 🏆 **Top Performer**: High traffic, low difficulty, good market size
- ✅ **Good**: Meets minimum criteria for viable keywords
- ❌ **Weak**: No difficulty data available
- 🔴 **Too Difficult**: Difficulty ≥ 4.0
- 📉 **Low Traffic**: Below minimum traffic threshold
- 💸 **Low Market**: Below market size threshold

Focus on Top Performers and Good keywords for your ASO strategy.`
        }
      }
    ]
  })
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("ASO Agent MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});