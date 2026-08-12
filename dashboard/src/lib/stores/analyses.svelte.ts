import type { AIAnalysis } from '$lib/ws/parse';

export class AnalysisStore {
	private latestByTicker = $state<Record<string, AIAnalysis>>({});

	set(analysis: AIAnalysis) {
		this.latestByTicker[analysis.ticker] = analysis;
	}

	latest(ticker: string): AIAnalysis | undefined {
		return this.latestByTicker[ticker];
	}
}

export const analysisStore = new AnalysisStore();
