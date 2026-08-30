import { env } from '$env/dynamic/private';
import type { PageServerLoad } from './$types';
import { INTERVALS, TICKERS, type CandleWire, type IndicatorWire } from '$lib/analytics';

const GATEWAY_HTTP_URL = env.GATEWAY_HTTP_URL ?? 'http://localhost:8080';

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
	return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : fallback;
}

export const load: PageServerLoad = async ({ url, fetch }) => {
	const ticker = pick(url.searchParams.get('ticker'), TICKERS, 'BBCA');
	const interval = pick(url.searchParams.get('interval'), INTERVALS, '1m');

	let candles: CandleWire[] = [];
	let indicators: IndicatorWire[] = [];
	let summary: IndicatorWire[] = [];

	try {
		const [candlesRes, indicatorsRes, summaryRes] = await Promise.all([
			fetch(`${GATEWAY_HTTP_URL}/candles?ticker=${ticker}&interval=${interval}&limit=500`),
			fetch(`${GATEWAY_HTTP_URL}/indicators?ticker=${ticker}&interval=${interval}&limit=500`),
			fetch(`${GATEWAY_HTTP_URL}/indicators/summary?interval=${interval}`)
		]);

		if (candlesRes.ok) {
			candles = ((await candlesRes.json()) as { candles: CandleWire[] }).candles ?? [];
		}
		if (indicatorsRes.ok) {
			indicators = ((await indicatorsRes.json()) as { indicators: IndicatorWire[] }).indicators ?? [];
		}
		if (summaryRes.ok) {
			summary = ((await summaryRes.json()) as { indicators: IndicatorWire[] }).indicators ?? [];
		}
	} catch (err) {
		console.error('failed to load analytics data', err);
	}

	return { ticker, interval, candles, indicators, summary };
};
