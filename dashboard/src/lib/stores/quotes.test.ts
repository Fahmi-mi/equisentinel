import { describe, expect, it } from 'vitest';
import { QuoteStore, MAX_POINTS } from './quotes.svelte';
import type { StockQuote } from '$lib/ws/parse';

function makeQuote(ticker: string, time: number): StockQuote {
	return { ticker, open: time, high: time, low: time, close: time, volume: time, time };
}

describe('QuoteStore', () => {
	it('caps the buffer at MAX_POINTS per ticker, evicting the oldest entries', () => {
		const store = new QuoteStore();

		for (let i = 0; i < MAX_POINTS + 50; i++) {
			store.add(makeQuote('BBCA', i));
		}

		const buffer = store.latest('BBCA');
		expect(buffer).toHaveLength(MAX_POINTS);
		expect(buffer[0].time).toBe(50);
		expect(buffer.at(-1)?.time).toBe(MAX_POINTS + 49);
	});

	it('tracks separate tickers independently', () => {
		const store = new QuoteStore();

		store.add(makeQuote('BBCA', 1));
		store.add(makeQuote('GOTO', 2));

		expect(store.latest('BBCA')).toHaveLength(1);
		expect(store.latest('GOTO')).toHaveLength(1);
		expect(store.latest('TLKM')).toHaveLength(0);
	});
});
