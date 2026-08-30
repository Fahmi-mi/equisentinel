<script lang="ts">
	import { goto } from '$app/navigation';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';
	import AnalyticsChart from '$lib/components/AnalyticsChart.svelte';
	import type { PageData } from './$types';
	import { INTERVALS, TICKERS, type IndicatorWire } from '$lib/analytics';

	let { data }: { data: PageData } = $props();

	function selectTicker(ticker: string) {
		goto(`/analytics?ticker=${ticker}&interval=${data.interval}`, { replaceState: true });
	}

	function selectInterval(interval: string) {
		goto(`/analytics?ticker=${data.ticker}&interval=${interval}`, { replaceState: true });
	}

	const fmt = (value: number | null) => (value === null ? '–' : value.toFixed(2));

	const latest = $derived(data.candles.at(-1));
	const summaryRows = $derived(
		TICKERS.map((ticker) => data.summary.find((row: IndicatorWire) => row.ticker === ticker)).filter(
			(row): row is IndicatorWire => row !== undefined
		)
	);
</script>

<div class="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-4 sm:p-6">
	<header class="glass-panel flex items-center justify-between rounded-2xl px-6 py-4">
		<div>
			<h1 class="text-lg font-semibold tracking-tight">EquiSentinel Analytics</h1>
			<p class="text-muted text-sm">Historical candles &amp; technical indicators</p>
		</div>
		<div class="flex items-center gap-4">
			<a href="/" class="text-muted text-sm transition hover:text-white">← Live Monitor</a>
			<ThemeToggle />
		</div>
	</header>

	<div class="glass-panel flex flex-wrap items-center justify-between gap-3 rounded-2xl p-3">
		<nav class="flex flex-wrap gap-2">
			{#each TICKERS as ticker (ticker)}
				<button
					type="button"
					onclick={() => selectTicker(ticker)}
					class="rounded-xl px-4 py-2 text-sm font-medium transition {data.ticker === ticker
						? 'text-white'
						: 'text-muted hover:bg-black/5 dark:hover:bg-white/5'}"
					style={data.ticker === ticker
						? 'background: linear-gradient(135deg, var(--accent), var(--accent-2));'
						: ''}
				>
					{ticker}
				</button>
			{/each}
		</nav>
		<div class="flex items-center gap-2">
			{#each INTERVALS as interval (interval)}
				<button
					type="button"
					onclick={() => selectInterval(interval)}
					class="rounded-xl px-3 py-2 text-sm font-medium transition {data.interval === interval
						? 'text-white'
						: 'text-muted hover:bg-black/5 dark:hover:bg-white/5'}"
					style={data.interval === interval
						? 'background: linear-gradient(135deg, var(--accent), var(--accent-2));'
						: ''}
				>
					{interval}
				</button>
			{/each}
		</div>
	</div>

	<section class="glass-panel flex flex-col gap-4 rounded-2xl p-6">
		<div class="flex items-baseline justify-between">
			<h2 class="text-2xl font-semibold">{data.ticker} · {data.interval}</h2>
			{#if latest}
				<span class="font-mono text-xl">{latest.close.toLocaleString('id-ID')}</span>
			{/if}
		</div>
		<div class="h-[420px]">
			<AnalyticsChart candles={data.candles} indicators={data.indicators} />
		</div>
		<div class="text-muted flex flex-wrap gap-4 text-xs">
			<span class="flex items-center gap-1.5"><span class="h-0.5 w-4 rounded bg-amber-500"></span>SMA</span>
			<span class="flex items-center gap-1.5"><span class="h-0.5 w-4 rounded bg-sky-400"></span>EMA</span>
			<span class="flex items-center gap-1.5"><span class="h-0.5 w-4 rounded bg-slate-400"></span>Bollinger Bands</span>
			<span class="flex items-center gap-1.5"><span class="h-0.5 w-4 rounded bg-violet-400"></span>RSI</span>
		</div>
	</section>

	{#if summaryRows.length > 0}
		<section class="glass-panel overflow-x-auto rounded-2xl p-6">
			<h3 class="mb-4 text-sm font-semibold tracking-tight">Perbandingan Indikator · {data.interval}</h3>
			<table class="w-full min-w-[560px] text-sm">
				<thead>
					<tr class="text-muted border-b border-white/10 text-left text-xs uppercase tracking-wider">
						<th class="py-2 pr-4 font-medium">Ticker</th>
						<th class="py-2 pr-4 font-medium">RSI</th>
						<th class="py-2 pr-4 font-medium">SMA</th>
						<th class="py-2 pr-4 font-medium">EMA</th>
						<th class="py-2 pr-4 font-medium">BB Upper</th>
						<th class="py-2 pr-4 font-medium">BB Middle</th>
						<th class="py-2 font-medium">BB Lower</th>
					</tr>
				</thead>
				<tbody>
					{#each summaryRows as row (row.ticker)}
						<tr class="border-b border-white/5 last:border-0">
							<td class="py-2 pr-4 font-semibold">{row.ticker}</td>
							<td class="py-2 pr-4 font-mono">{fmt(row.rsi)}</td>
							<td class="py-2 pr-4 font-mono">{fmt(row.sma)}</td>
							<td class="py-2 pr-4 font-mono">{fmt(row.ema)}</td>
							<td class="py-2 pr-4 font-mono">{fmt(row.bollingerUpper)}</td>
							<td class="py-2 pr-4 font-mono">{fmt(row.bollingerMiddle)}</td>
							<td class="py-2 font-mono">{fmt(row.bollingerLower)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</section>
	{/if}
</div>
