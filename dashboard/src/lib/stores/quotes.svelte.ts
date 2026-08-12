import type { StockQuote } from '$lib/ws/parse';

export const MAX_POINTS = 500;

export class QuoteStore {
	private buffers = $state<Record<string, StockQuote[]>>({});

	add(quote: StockQuote) {
		const existing = this.buffers[quote.ticker] ?? [];
		const next = [...existing, quote];
		this.buffers[quote.ticker] =
			next.length > MAX_POINTS ? next.slice(next.length - MAX_POINTS) : next;
	}

	latest(ticker: string): StockQuote[] {
		return this.buffers[ticker] ?? [];
	}
}

export const quoteStore = new QuoteStore();
