<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		createChart,
		CandlestickSeries,
		type IChartApi,
		type ISeriesApi,
		type UTCTimestamp
	} from 'lightweight-charts';
	import { quoteStore } from '$lib/stores/quotes.svelte';

	let { ticker }: { ticker: string } = $props();

	let container: HTMLDivElement;
	let chart: IChartApi | undefined;
	let series: ISeriesApi<'Candlestick'> | undefined;

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

	onDestroy(() => {
		chart?.remove();
	});
</script>

<div bind:this={container} class="h-full w-full"></div>
