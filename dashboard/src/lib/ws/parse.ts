export interface StockQuote {
	ticker: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
	time: number;
}

interface StockQuoteWire {
	ticker: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: string;
	timestamp: string;
}

export type Sentiment = 'BULLISH' | 'BEARISH' | 'NEUTRAL';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface AIAnalysis {
	correlationId: string;
	ticker: string;
	summary: string;
	sentiment: Sentiment;
	riskLevel: RiskLevel;
	modelUsed: string;
	latencyMs: number;
}

interface AIAnalysisWire {
	correlationId: string;
	ticker: string;
	summary: string;
	sentiment: string;
	riskLevel: string;
	modelUsed: string;
	latencyMs: number;
}

type GatewayEnvelope =
	| { type: 'quote'; data: StockQuoteWire }
	| { type: 'ai_analysis'; data: AIAnalysisWire };

export type GatewayMessage =
	| { type: 'quote'; quote: StockQuote }
	| { type: 'ai_analysis'; analysis: AIAnalysis };

function stripEnumPrefix(value: string, prefix: string): string {
	return value.startsWith(prefix) ? value.slice(prefix.length) : value;
}

export function parseGatewayMessage(raw: string): GatewayMessage {
	const envelope = JSON.parse(raw) as GatewayEnvelope;

	if (envelope.type === 'quote') {
		const wire = envelope.data;
		return {
			type: 'quote',
			quote: {
				ticker: wire.ticker,
				open: wire.open,
				high: wire.high,
				low: wire.low,
				close: wire.close,
				volume: Number(wire.volume),
				time: Math.floor(new Date(wire.timestamp).getTime() / 1000)
			}
		};
	}

	const wire = envelope.data;
	return {
		type: 'ai_analysis',
		analysis: {
			correlationId: wire.correlationId,
			ticker: wire.ticker,
			summary: wire.summary,
			sentiment: stripEnumPrefix(wire.sentiment, 'SENTIMENT_') as Sentiment,
			riskLevel: stripEnumPrefix(wire.riskLevel, 'RISK_LEVEL_') as RiskLevel,
			modelUsed: wire.modelUsed,
			latencyMs: wire.latencyMs
		}
	};
}
