import fetch from 'node-fetch';
import { ASOAnalysisRequest, ASOAnalysisResponse, StreamEvent } from './types.js';
import { Readable } from 'stream';

export class ASOAPIClient {
  private baseUrl: string;
  private authToken?: string;

  constructor(baseUrl: string = 'http://localhost:8080', authToken?: string) {
    this.baseUrl = baseUrl;
    this.authToken = authToken;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }
    
    return headers;
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return response.ok;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  async analyzeAppIdeas(request: ASOAnalysisRequest): Promise<ASOAnalysisResponse> {
    const payload = {
      message: request.message,
      model: request.model || 'gpt-4o-mini',
      thread_id: request.thread_id,
      user_id: request.user_id,
      agent_config: {
        market_threshold: request.market_threshold || 50000,
        keywords_per_idea: request.keywords_per_idea || 30
      }
    };

    try {
      const response = await fetch(`${this.baseUrl}/invoke`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json() as ASOAnalysisResponse;
      return result;
    } catch (error) {
      throw new Error(`API request failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async *streamAnalysis(request: ASOAnalysisRequest): AsyncGenerator<StreamEvent, void, unknown> {
    const payload = {
      message: request.message,
      model: request.model || 'gpt-4o-mini',
      thread_id: request.thread_id,
      user_id: request.user_id,
      stream_tokens: true,
      agent_config: {
        market_threshold: request.market_threshold || 50000,
        keywords_per_idea: request.keywords_per_idea || 30
      }
    };

    try {
      const response = await fetch(`${this.baseUrl}/stream`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const stream = response.body as unknown as Readable;
      let buffer = '';

      for await (const chunk of stream) {
        buffer += chunk.toString();
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim() === '') continue;
          if (line === 'data: [DONE]') return;
          
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6));
              yield {
                type: eventData.type,
                content: eventData.content,
                timestamp: new Date().toISOString()
              };
            } catch (parseError) {
              console.error('Failed to parse SSE data:', parseError);
            }
          }
        }
      }
    } catch (error) {
      throw new Error(`Streaming failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}