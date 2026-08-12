<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		createChart,
		CandlestickSeries,
		createSeriesMarkers,
		type IChartApi,
		type ISeriesApi,
		type ISeriesMarkersPluginApi,
		type SeriesMarker,
		type Time,
		type UTCTimestamp
	} from 'lightweight-charts';
	import { quoteStore } from '$lib/stores/quotes.svelte';
	import { analysisStore, type TimedAnalysis } from '$lib/stores/analyses.svelte';

	let { ticker }: { ticker: string } = $props();

	let container: HTMLDivElement;
	let chart: IChartApi | undefined;
	let series: ISeriesApi<'Candlestick'> | undefined;
	let markers: ISeriesMarkersPluginApi<Time> | undefined;

	const markerStyle = {
		BULLISH: { shape: 'arrowUp', position: 'belowBar', color: '#34d399' },
		BEARISH: { shape: 'arrowDown', position: 'aboveBar', color: '#f87171' },
		NEUTRAL: { shape: 'circle', position: 'aboveBar', color: '#94a3b8' }
	} as const;

	function toMarker(analysis: TimedAnalysis): SeriesMarker<Time> {
		const style = markerStyle[analysis.sentiment];
		return {
			time: analysis.time as UTCTimestamp,
			position: style.position,
			color: style.color,
			shape: style.shape,
			text: analysis.riskLevel
		};
	}

	onMount(() => {
		chart = createChart(container, {
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
		});

		series = chart.addSeries(CandlestickSeries, {
			upColor: '#34d399',
			downColor: '#f87171',
			borderVisible: false,
			wickUpColor: '#34d399',
			wickDownColor: '#f87171'
		});

		markers = createSeriesMarkers(series, []);
	});

	$effect(() => {
		if (!series) return;
		const points = quoteStore.latest(ticker);
		series.setData(
			points.map((q) => ({
				time: q.time as UTCTimestamp,
				open: q.open,
				high: q.high,
				low: q.low,
				close: q.close
			}))
		);
	});

	$effect(() => {
		if (!markers) return;
		markers.setMarkers(analysisStore.history(ticker).map(toMarker));
	});

	onDestroy(() => {
		chart?.remove();
	});
</script>

<div bind:this={container} class="h-full w-full"></div>
