import type { AIAnalysis } from '$lib/ws/parse';

export interface TimedAnalysis extends AIAnalysis {
	time: number;
}

export const MAX_HISTORY = 200;

export class AnalysisStore {
	private byTicker = $state<Record<string, TimedAnalysis[]>>({});

	add(analysis: TimedAnalysis) {
		const existing = this.byTicker[analysis.ticker] ?? [];
		const next = [...existing, analysis];
		this.byTicker[analysis.ticker] =
			next.length > MAX_HISTORY ? next.slice(next.length - MAX_HISTORY) : next;
	}

	latest(ticker: string): TimedAnalysis | undefined {
		return this.byTicker[ticker]?.at(-1);
	}

	history(ticker: string): TimedAnalysis[] {
		return this.byTicker[ticker] ?? [];
	}
}

export const analysisStore = new AnalysisStore();
