import { describe, expect, it } from 'vitest';
import { parseQuoteMessage } from './parse';

describe('parseQuoteMessage', () => {
	it('parses a protojson-encoded StockQuote message', () => {
		const raw = JSON.stringify({
			ticker: 'BBCA',
			open: 9000,
			high: 9100,
			low: 8950,
			close: 9050,
			volume: '1500000',
			timestamp: '2026-08-06T07:32:22Z'
		});

		const quote = parseQuoteMessage(raw);

		expect(quote.ticker).toBe('BBCA');
		expect(quote.close).toBe(9050);
		expect(quote.volume).toBe(1500000);
		expect(quote.time).toBe(Math.floor(new Date('2026-08-06T07:32:22Z').getTime() / 1000));
	});

	it('throws on malformed JSON', () => {
		expect(() => parseQuoteMessage('not json')).toThrow();
	});
});
