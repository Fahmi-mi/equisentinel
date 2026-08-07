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

export function parseQuoteMessage(raw: string): StockQuote {
	const wire = JSON.parse(raw) as StockQuoteWire;

	return {
		ticker: wire.ticker,
		open: wire.open,
		high: wire.high,
		low: wire.low,
		close: wire.close,
		volume: Number(wire.volume),
		time: Math.floor(new Date(wire.timestamp).getTime() / 1000)
	};
}
