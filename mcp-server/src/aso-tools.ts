import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { ASOAPIClient } from './api-client.js';
import { ASOAnalysisRequest, ASOAnalysisResponse, KeywordMetrics, ProgressUpdate, IntermediateResult, ASOAnalysisReport } from './types.js';

// Logging utility for MCP servers (uses stderr to avoid interfering with JSON-RPC on stdout)
const logger = {
  info: (message: string, ...args: any[]) => console.error(`[INFO] ${message}`, ...args),
  error: (message: string, ...args: any[]) => console.error(`[ERROR] ${message}`, ...args),
  warn: (message: string, ...args: any[]) => console.error(`[WARN] ${message}`, ...args),
  debug: (message: string, ...args: any[]) => console.error(`[DEBUG] ${message}`, ...args)
};

// Get configuration from environment
const ASO_SERVICE_URL = process.env.ASO_SERVICE_URL || 'http://localhost:8080';
const ASO_AUTH_TOKEN = process.env.ASO_AUTH_TOKEN || process.env.AUTH_SECRET;

const client = new ASOAPIClient(ASO_SERVICE_URL, ASO_AUTH_TOKEN);

export function registerASOTools(server: McpServer) {
  // Main ASO analysis tool with streaming support
  server.registerTool(
    "analyze-app-ideas",
    {
      title: "ASO Analysis with Progress Updates",
      description: "Analyze app ideas for ASO opportunities with real-time progress updates. Provides keyword difficulty, traffic metrics, and market size analysis.",
      inputSchema: {
        message: z.string().describe("Describe the app ideas to analyze (e.g., 'fitness tracking apps', 'meditation apps for anxiety')"),
        model: z.string().optional().default("gpt-4o-mini").describe("LLM model to use for analysis"),
        market_threshold: z.number().optional().default(50000).describe("Minimum market size threshold in USD"),
        keywords_per_idea: z.number().optional().default(30).describe("Number of keywords to generate per app idea"),
        stream: z.boolean().optional().default(true).describe("Enable streaming for real-time updates"),
        user_id: z.string().optional().describe("User ID for tracking"),
        thread_id: z.string().optional().describe("Thread ID for conversation context")
      }
    },
    async ({ message, model, market_threshold, keywords_per_idea, stream, user_id, thread_id }, { sendNotification }) => {
      logger.info("🔧 ASO Tool called with params:", {
        message: message.substring(0, 100) + "...",
        model,
        market_threshold,
        keywords_per_idea,
        stream,
        user_id,
        thread_id,
        hasNotificationHandler: !!sendNotification
      });
      
      const request: ASOAnalysisRequest = {
        message,
        model,
        market_threshold,
        keywords_per_idea,
        user_id,
        thread_id
      };

      // Check service health first
      logger.info("🏥 Checking ASO service health...");
      const isHealthy = await client.checkHealth();
      if (!isHealthy) {
        logger.error("❌ ASO service is not healthy");
        return {
          content: [{
            type: "text",
            text: "❌ **ASO Service Unavailable**\n\nThe ASO analysis service is not running. Please ensure the service is started on http://localhost:8080"
          }]
        };
      }
      logger.info("✅ ASO service is healthy");

      try {
        if (stream) {
          // Use streaming for real-time updates
          logger.info("🌊 Starting streaming analysis...");
          let finalReport: ASOAnalysisReport | null = null;
          let streamedContent = "🚀 **Starting ASO Analysis**\n\nAnalyzing app ideas with real-time progress updates...\n\n";

          for await (const event of client.streamAnalysis(request)) {
            logger.debug("📦 Received streaming event:", {
              type: event.type,
              content: typeof event.content === 'object' ? JSON.stringify(event.content).substring(0, 200) + "..." : event.content
            });
            switch (event.type) {
              case "progress":
                const progress = event.content as ProgressUpdate;
                const stepProgress = Math.round(progress.progress_percentage);
                
                // Send MCP progress notification
                const progressMessage = `📊 ${progress.node_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}: ${progress.status_message} (${stepProgress}%)`;
                logger.info("📤 Sending progress notification:", progressMessage);
                
                try {
                  await sendNotification({
                    method: "notifications/message",
                    params: {
                      level: "info",
                      data: progressMessage
                    }
                  });
                  logger.info("✅ Progress notification sent successfully");
                } catch (notificationError) {
                  logger.error("❌ Failed to send progress notification:", notificationError);
                }
                
                streamedContent += `📊 **${progress.node_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}** - ${progress.status_message} (${stepProgress}%)\n`;
                break;

              case "intermediate":
                const intermediate = event.content as IntermediateResult;
                
                // Send intermediate results as progress notifications
                const intermediateMessage = `📝 Intermediate result: ${intermediate.result_type.replace(/_/g, ' ')}`;
                logger.info("📤 Sending intermediate notification:", intermediateMessage);
                
                try {
                  await sendNotification({
                    method: "notifications/message",
                    params: {
                      level: "info",
                      data: intermediateMessage
                    }
                  });
                  logger.info("✅ Intermediate notification sent successfully");
                } catch (notificationError) {
                  logger.error("❌ Failed to send intermediate notification:", notificationError);
                }
                
                streamedContent += formatIntermediateResult(intermediate);
                break;

              case "message":
                const messageContent = event.content;
                if (typeof messageContent === 'object' && messageContent.content) {
                  streamedContent += `💬 ${messageContent.content}\n`;
                }
                
                // Check for final report
                if (messageContent.custom_data?.final_report) {
                  finalReport = messageContent.custom_data.final_report;
                }
                break;

              case "interrupt":
                streamedContent += `❓ **Clarification Needed**: ${event.content.message || 'Agent needs more information'}\n`;
                break;

              case "error":
                streamedContent += `❌ **Error**: ${event.content}\n`;
                break;
            }
          }

          // Send final progress notification
          logger.info("📤 Sending final notification: ASO Analysis Complete");
          
          try {
            await sendNotification({
              method: "notifications/message",
              params: {
                level: "info",
                data: "✅ ASO Analysis Complete"
              }
            });
            logger.info("✅ Final notification sent successfully");
          } catch (notificationError) {
            logger.error("❌ Failed to send final notification:", notificationError);
          }

          // Format final results
          if (finalReport) {
            const formattedReport = formatAnalysisReport(finalReport, market_threshold || 50000);
            streamedContent += `\n\n${formattedReport}`;
          }

          streamedContent += "\n\n✅ **ASO Analysis Complete**\n\nAnalysis finished successfully!";

          logger.info("📊 Analysis completed, returning results. Content length:", streamedContent.length);

          return {
            content: [{
              type: "text",
              text: streamedContent
            }]
          };

        } else {
          // Non-streaming analysis
          const result = await client.analyzeAppIdeas(request);
          const formattedResult = formatNonStreamingResult(result, market_threshold || 50000);
          
          return {
            content: [{
              type: "text",
              text: formattedResult
            }]
          };
        }
      } catch (error) {
        logger.error("💥 Analysis failed with error:", error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        
        // Try to send error notification
        try {
          await sendNotification({
            method: "notifications/message",
            params: {
              level: "error",
              data: `❌ Analysis failed: ${errorMessage}`
            }
          });
          logger.info("📤 Error notification sent");
        } catch (notificationError) {
          logger.error("❌ Failed to send error notification:", notificationError);
        }
        
        return {
          content: [{
            type: "text",
            text: `❌ **Analysis Failed**\n\n${errorMessage}`
          }]
        };
      }
    }
  );

  // Service health check tool
  server.registerTool(
    "check-aso-service",
    {
      title: "ASO Service Health Check",
      description: "Check if the ASO analysis service is running and healthy",
      inputSchema: {}
    },
    async () => {
      logger.info("🏥 Health check tool called");
      const isHealthy = await client.checkHealth();
      logger.info("🏥 Health check result:", isHealthy);
      
      return {
        content: [{
          type: "text",
          text: isHealthy 
            ? "✅ **ASO Service Status**: Healthy and ready to analyze app ideas."
            : "❌ **ASO Service Status**: Service is not available. Please check if the service is running on http://localhost:8080"
        }]
      };
    }
  );
}

function formatIntermediateResult(result: IntermediateResult): string {
  switch (result.result_type) {
    case "keywords_found":
      const keywordsData = result.data.keywords || {};
      const totalKeywords = Object.values(keywordsData).reduce((sum: number, keywords: any) => sum + (keywords?.length || 0), 0);
      return `📝 **Keywords Generated**: ${totalKeywords} keywords across ${Object.keys(keywordsData).length} app ideas\n`;

    case "apps_found":
      const totalApps = result.data.total_apps || 0;
      return `📱 **Apps Found**: ${totalApps} apps found for keyword analysis\n`;

    case "market_size_calculated":
      const revenueData = result.data.revenue_by_keyword || {};
      const topKeywords = Object.entries(revenueData)
        .sort(([,a], [,b]) => (b as number) - (a as number))
        .slice(0, 3);
      
      if (topKeywords.length > 0) {
        let output = `💰 **Market Size Analysis**: Top opportunities:\n`;
        topKeywords.forEach(([keyword, revenue]) => {
          output += `  • ${keyword}: $${(revenue as number).toLocaleString()}\n`;
        });
        return output;
      }
      return `💰 **Market Size Analysis**: Analysis completed\n`;

    default:
      return `📊 **${result.result_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}**: Data processed\n`;
  }
}

function formatAnalysisReport(report: ASOAnalysisReport, marketThreshold: number): string {
  if (!report.app_ideas || Object.keys(report.app_ideas).length === 0) {
    return "**No analysis results available.**";
  }

  let output = "## 📊 ASO Analysis Results\n\n";
  
  // Add metadata
  const metadata = report.analysis_metadata;
  output += "### Analysis Summary\n";
  output += `- **Keywords Analyzed**: ${metadata.total_keywords_analyzed}\n`;
  output += `- **Difficulty Analyses**: ${metadata.difficulty_analyses_completed}\n`;
  output += "\n";

  // Process each app idea
  for (const [idea, analysis] of Object.entries(report.app_ideas)) {
    output += `### 🎯 ${idea.replace(/\b\w/g, l => l.toUpperCase())}\n\n`;
    
    const marketSize = analysis.best_possible_market_size_usd;
    const keywordsData = analysis.keywords;
    
    output += `**Best Market Opportunity**: $${marketSize.toLocaleString()}\n`;
    output += `**Keywords Analyzed**: ${Object.keys(keywordsData).length}\n\n`;

    // Find top performing keywords
    const topKeywords = getTopPerformingKeywords(keywordsData, marketThreshold);
    
    if (topKeywords.length > 0) {
      output += "**🏆 Top Performing Keywords:**\n\n";
      topKeywords.forEach((kw, index) => {
        output += `${index + 1}. **${kw.keyword}**\n`;
        output += `   - Difficulty: ${kw.difficulty.toFixed(1)}/10\n`;
        output += `   - Traffic: ${kw.traffic.toFixed(0)}/100\n`;
        output += `   - Market Size: $${kw.market_size.toLocaleString()}\n`;
        output += `   - Opportunity Score: ${kw.opportunity_score.toFixed(1)}\n\n`;
      });
    } else {
      output += `⚠️ No keywords meet the top performer criteria (Traffic ≥ 200, Difficulty < 3.0, Market Size ≥ $${marketThreshold.toLocaleString()})\n\n`;
    }
  }

  return output;
}

function formatNonStreamingResult(result: ASOAnalysisResponse, marketThreshold: number): string {
  let output = "## 📊 ASO Analysis Results\n\n";
  
  if (result.content) {
    output += `**Response**: ${result.content}\n\n`;
  }

  if (result.custom_data?.final_report) {
    output += formatAnalysisReport(result.custom_data.final_report, marketThreshold);
  }

  return output;
}

function getTopPerformingKeywords(keywordsData: Record<string, any>, marketThreshold: number): KeywordMetrics[] {
  const topKeywords: KeywordMetrics[] = [];
  
  for (const [keyword, data] of Object.entries(keywordsData)) {
    const difficulty = data.difficulty_rating || 0;
    const traffic = data.traffic_rating || 0;
    const marketSize = data.market_size_usd || 0;
    
    // Top performer criteria: Traffic >= 200, Difficulty < 3.0, Market Size >= threshold
    if (traffic >= 200 && difficulty < 3.0 && marketSize >= marketThreshold) {
      topKeywords.push({
        keyword,
        difficulty,
        traffic,
        market_size: marketSize,
        status: "top_performer",
        opportunity_score: traffic / Math.max(difficulty, 1)
      });
    }
  }
  
  // Sort by opportunity score (traffic/difficulty ratio)
  topKeywords.sort((a, b) => b.opportunity_score - a.opportunity_score);
  
  return topKeywords.slice(0, 3); // Return top 3
}