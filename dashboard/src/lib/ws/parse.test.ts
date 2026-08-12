import { describe, expect, it } from 'vitest';
import { parseGatewayMessage } from './parse';

describe('parseGatewayMessage', () => {
	it('parses a quote envelope', () => {
		const raw = JSON.stringify({
			type: 'quote',
			data: {
				ticker: 'BBCA',
				open: 9000,
				high: 9100,
				low: 8950,
				close: 9050,
				volume: '1500000',
				timestamp: '2026-08-06T07:32:22Z'
			}
		});

		const message = parseGatewayMessage(raw);

		if (message.type !== 'quote') throw new Error('expected quote message');
		expect(message.quote.ticker).toBe('BBCA');
		expect(message.quote.close).toBe(9050);
		expect(message.quote.volume).toBe(1500000);
		expect(message.quote.time).toBe(Math.floor(new Date('2026-08-06T07:32:22Z').getTime() / 1000));
	});

	it('parses an ai_analysis envelope and strips enum prefixes', () => {
		const raw = JSON.stringify({
			type: 'ai_analysis',
			data: {
				correlationId: 'corr-1',
				ticker: 'GOTO',
				summary: 'Sentimen negatif akibat divestasi.',
				sentiment: 'SENTIMENT_BEARISH',
				riskLevel: 'RISK_LEVEL_HIGH',
				modelUsed: 'deepseek-chat',
				latencyMs: 1234
			}
		});

		const message = parseGatewayMessage(raw);

		if (message.type !== 'ai_analysis') throw new Error('expected ai_analysis message');
		expect(message.analysis.ticker).toBe('GOTO');
		expect(message.analysis.sentiment).toBe('BEARISH');
		expect(message.analysis.riskLevel).toBe('HIGH');
		expect(message.analysis.latencyMs).toBe(1234);
	});

	it('throws on malformed JSON', () => {
		expect(() => parseGatewayMessage('not json')).toThrow();
	});
});
