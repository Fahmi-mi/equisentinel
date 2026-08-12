import type { AIAnalysis } from '$lib/ws/parse';

export type FeedbackValue = 'ACCURATE' | 'INACCURATE';

export interface TimedAnalysis extends AIAnalysis {
	time: number;
	feedback?: FeedbackValue | null;
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

	setFeedback(ticker: string, correlationId: string, feedback: FeedbackValue) {
		const list = this.byTicker[ticker];
		if (!list) return;
		const index = list.findIndex((a) => a.correlationId === correlationId);
		if (index === -1) return;
		list[index] = { ...list[index], feedback };
	}

	latest(ticker: string): TimedAnalysis | undefined {
		return this.byTicker[ticker]?.at(-1);
	}

	history(ticker: string): TimedAnalysis[] {
		return this.byTicker[ticker] ?? [];
	}
}

export const analysisStore = new AnalysisStore();
