<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		createChart,
		CandlestickSeries,
		LineSeries,
		LineStyle,
		type IChartApi,
		type ISeriesApi,
		type Time,
		type UTCTimestamp
	} from 'lightweight-charts';
	import type { CandleWire, IndicatorWire } from '$lib/analytics';

	let { candles, indicators }: { candles: CandleWire[]; indicators: IndicatorWire[] } = $props();

	let container: HTMLDivElement;
	let chart: IChartApi | undefined;
	let candleSeries: ISeriesApi<'Candlestick'> | undefined;
	let smaSeries: ISeriesApi<'Line'> | undefined;
	let emaSeries: ISeriesApi<'Line'> | undefined;
	let bbUpperSeries: ISeriesApi<'Line'> | undefined;
	let bbMiddleSeries: ISeriesApi<'Line'> | undefined;
	let bbLowerSeries: ISeriesApi<'Line'> | undefined;
	let rsiSeries: ISeriesApi<'Line'> | undefined;

	const timeOf = (ts: string) => Math.floor(new Date(ts).getTime() / 1000) as UTCTimestamp;

	const chartOptions = {
		autoSize: true,
		layout: {
			background: { color: 'transparent' },
			textColor: 'rgba(148, 163, 184, 0.9)'
		},
		grid: {
			vertLines: { color: 'rgba(148, 163, 184, 0.08)' },
			horzLines: { color: 'rgba(148, 163, 184, 0.08)' }
		},
		timeScale: { borderColor: 'rgba(148, 163, 184, 0.15)' },
		rightPriceScale: { borderColor: 'rgba(148, 163, 184, 0.15)' }
	} as const;

	function overlayOptions(color: string, dashed = false) {
		return {
			color,
			lineWidth: 1 as const,
			lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
			priceLineVisible: false,
			lastValueVisible: false,
			crosshairMarkerVisible: false
		};
	}

	function toLine(rows: IndicatorWire[], field: keyof IndicatorWire): { time: Time; value: number }[] {
		return rows
			.map((row) => ({ time: timeOf(row.timestamp), value: row[field] as number | null }))
			.filter((p) => p.value !== null) as { time: Time; value: number }[];
	}

	onMount(() => {
		chart = createChart(container, chartOptions);

		candleSeries = chart.addSeries(CandlestickSeries, {
			upColor: '#34d399',
			downColor: '#f87171',
			borderVisible: false,
			wickUpColor: '#34d399',
			wickDownColor: '#f87171'
		});

		smaSeries = chart.addSeries(LineSeries, overlayOptions('#f59e0b'));
		emaSeries = chart.addSeries(LineSeries, overlayOptions('#38bdf8'));
		bbUpperSeries = chart.addSeries(LineSeries, overlayOptions('rgba(148, 163, 184, 0.8)', true));
		bbMiddleSeries = chart.addSeries(LineSeries, overlayOptions('rgba(148, 163, 184, 0.8)'));
		bbLowerSeries = chart.addSeries(LineSeries, overlayOptions('rgba(148, 163, 184, 0.8)', true));

		rsiSeries = chart.addSeries(LineSeries, overlayOptions('#a78bfa'), 1);
		rsiSeries.applyOptions({ lastValueVisible: true });
		rsiSeries.createPriceLine({
			price: 70,
			color: 'rgba(248, 113, 113, 0.45)',
			lineWidth: 1,
			lineStyle: LineStyle.Dashed,
			axisLabelVisible: false,
			title: ''
		});
		rsiSeries.createPriceLine({
			price: 30,
			color: 'rgba(52, 211, 153, 0.45)',
			lineWidth: 1,
			lineStyle: LineStyle.Dashed,
			axisLabelVisible: false,
			title: ''
		});
	});

	$effect(() => {
		if (!candleSeries) return;
		candleSeries.setData(
			candles.map((c) => ({
				time: timeOf(c.bucketStart),
				open: c.open,
				high: c.high,
				low: c.low,
				close: c.close
			}))
		);
	});

	$effect(() => {
		if (!smaSeries) return;
		smaSeries.setData(toLine(indicators, 'sma'));
		emaSeries?.setData(toLine(indicators, 'ema'));
		bbUpperSeries?.setData(toLine(indicators, 'bollingerUpper'));
		bbMiddleSeries?.setData(toLine(indicators, 'bollingerMiddle'));
		bbLowerSeries?.setData(toLine(indicators, 'bollingerLower'));
	});

	$effect(() => {
		if (!rsiSeries) return;
		rsiSeries.setData(toLine(indicators, 'rsi'));
	});

	onDestroy(() => {
		chart?.remove();
	});
</script>

<div bind:this={container} class="h-full w-full"></div>
