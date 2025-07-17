export interface ASOAnalysisRequest {
  message: string;
  model?: string;
  market_threshold?: number;
  keywords_per_idea?: number;
  user_id?: string;
  thread_id?: string;
}

export interface ASOAnalysisResponse {
  type: string;
  content: string;
  tool_calls?: any[];
  tool_call_id?: string;
  run_id?: string;
  response_metadata?: Record<string, any>;
  custom_data?: {
    final_report?: ASOAnalysisReport;
  };
}

export interface ASOAnalysisReport {
  timestamp: string;
  analysis_metadata: {
    total_keywords_analyzed: number;
    difficulty_analyses_completed: number;
    total_market_size_usd: number;
    store_usage?: {
      active_items: number;
      total_items: number;
      namespaces: number;
    };
  };
  app_ideas: Record<string, AppIdeaAnalysis>;
}

export interface AppIdeaAnalysis {
  best_possible_market_size_usd: number;
  keywords: Record<string, KeywordAnalysis>;
}

export interface KeywordAnalysis {
  difficulty_rating: number;
  traffic_rating: number;
  market_size_usd: number;
}

export interface StreamEvent {
  type: "message" | "progress" | "intermediate" | "interrupt" | "error" | "complete";
  content: any;
  timestamp?: string;
}

export interface ProgressUpdate {
  node_name: string;
  progress_percentage: number;
  status_message: string;
  correlation_id?: string;
}

export interface IntermediateResult {
  result_type: string;
  data: Record<string, any>;
  timestamp: string;
}

export interface KeywordMetrics {
  keyword: string;
  difficulty: number;
  traffic: number;
  market_size: number;
  status: "top_performer" | "good" | "low_potential" | "too_difficult" | "low_traffic" | "low_market" | "weak";
  opportunity_score: number;
}