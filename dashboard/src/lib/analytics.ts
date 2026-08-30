export const TICKERS = ['BBCA', 'BBRI', 'TLKM', 'ASII', 'GOTO'];
export const INTERVALS = ['1m', '5m', '1h'] as const;
export type Interval = (typeof INTERVALS)[number];

export interface CandleWire {
	bucketStart: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: string;
	tickCount: number;
}

export interface IndicatorWire {
	ticker: string;
	timestamp: string;
	sma: number | null;
	ema: number | null;
	rsi: number | null;
	bollingerUpper: number | null;
	bollingerMiddle: number | null;
	bollingerLower: number | null;
}
