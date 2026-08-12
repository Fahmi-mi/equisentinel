import { env } from '$env/dynamic/private';
import { toStockQuote, type RiskLevel, type Sentiment, type StockQuote, type StockQuoteWire } from '$lib/ws/parse';
import type { FeedbackValue, TimedAnalysis } from '$lib/stores/analyses.svelte';
import type { PageServerLoad } from './$types';

const TICKERS = ['BBCA', 'BBRI', 'TLKM', 'ASII', 'GOTO'];
const GATEWAY_HTTP_URL = env.GATEWAY_HTTP_URL ?? 'http://localhost:8080';

interface AnalysisWire {
	correlationId: string;
	ticker: string;
	summary: string;
	sentiment: string;
	riskLevel: string;
	modelUsed: string;
	latencyMs: number;
	createdAt: string;
	feedback?: string;
}

function toTimedAnalysis(wire: AnalysisWire): TimedAnalysis {
	return {
		correlationId: wire.correlationId,
		ticker: wire.ticker,
		summary: wire.summary,
		sentiment: wire.sentiment as Sentiment,
		riskLevel: wire.riskLevel as RiskLevel,
		modelUsed: wire.modelUsed,
		latencyMs: wire.latencyMs,
		time: Math.floor(new Date(wire.createdAt).getTime() / 1000),
		feedback: (wire.feedback as FeedbackValue | undefined) ?? null
	};
}

export const load: PageServerLoad = async ({ fetch }) => {
	const history: Record<string, StockQuote[]> = {};
	const analysisHistory: Record<string, TimedAnalysis[]> = {};

	await Promise.all(
		TICKERS.map(async (ticker) => {
			try {
				const [priceRes, analysisRes] = await Promise.all([
					fetch(`${GATEWAY_HTTP_URL}/history?ticker=${ticker}`),
					fetch(`${GATEWAY_HTTP_URL}/analyses?ticker=${ticker}`)
				]);

				if (priceRes.ok) {
					const body: { quotes: StockQuoteWire[] } = await priceRes.json();
					history[ticker] = body.quotes.map(toStockQuote);
				}

				if (analysisRes.ok) {
					const body: { analyses: AnalysisWire[] } = await analysisRes.json();
					analysisHistory[ticker] = body.analyses.map(toTimedAnalysis);
				}
			} catch (err) {
				console.error('failed to load history', ticker, err);
			}
		})
	);

	return { history, analysisHistory };
};
