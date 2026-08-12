<script lang="ts">
	import { onMount } from 'svelte';
	import { GatewaySocket } from '$lib/ws/client.svelte';
	import { quoteStore } from '$lib/stores/quotes.svelte';
	import { analysisStore, type FeedbackValue } from '$lib/stores/analyses.svelte';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';
	import CandlestickChart from '$lib/components/CandlestickChart.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const TICKERS = ['BBCA', 'BBRI', 'TLKM', 'ASII', 'GOTO'];
	const GATEWAY_WS_URL = import.meta.env.VITE_GATEWAY_WS_URL ?? 'ws://localhost:8080/ws';

	let activeTicker = $state(TICKERS[0]);
	const socket = new GatewaySocket(GATEWAY_WS_URL);

	onMount(() => {
		for (const quotes of Object.values(data.history)) {
			for (const quote of quotes) quoteStore.add(quote);
		}
		for (const analyses of Object.values(data.analysisHistory)) {
			for (const analysis of analyses) analysisStore.add(analysis);
		}
		socket.connect();
		return () => socket.disconnect();
	});

	const statusMeta = {
		connecting: { label: 'Connecting…', dot: 'bg-amber-400' },
		open: { label: 'Live', dot: 'bg-emerald-400' },
		closed: { label: 'Disconnected', dot: 'bg-rose-400' }
	} as const;

	const latestQuote = $derived(quoteStore.latest(activeTicker).at(-1));
	const latestAnalysis = $derived(analysisStore.latest(activeTicker));

	const sentimentMeta = {
		BULLISH: { label: 'Bullish', class: 'bg-emerald-500/15 text-emerald-500' },
		BEARISH: { label: 'Bearish', class: 'bg-rose-500/15 text-rose-500' },
		NEUTRAL: { label: 'Neutral', class: 'bg-slate-500/15 text-slate-400' }
	} as const;

	const riskMeta = {
		LOW: { label: 'Low Risk', class: 'bg-emerald-500/15 text-emerald-500' },
		MEDIUM: { label: 'Medium Risk', class: 'bg-amber-500/15 text-amber-500' },
		HIGH: { label: 'High Risk', class: 'bg-rose-500/15 text-rose-500' }
	} as const;

	let submittingFeedback = $state(false);

	async function submitFeedback(value: FeedbackValue) {
		if (!latestAnalysis || submittingFeedback) return;
		const { correlationId, ticker } = latestAnalysis;

		submittingFeedback = true;
		try {
			const res = await fetch('/api/feedback', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ correlationId, feedbackValue: value })
			});
			if (!res.ok) throw new Error(`feedback request failed with status ${res.status}`);
			analysisStore.setFeedback(ticker, correlationId, value);
		} catch (err) {
			console.error('failed to submit feedback', err);
		} finally {
			submittingFeedback = false;
		}
	}
</script>

<div class="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-4 sm:p-6">
	<header class="glass-panel flex items-center justify-between rounded-2xl px-6 py-4">
		<div>
			<h1 class="text-lg font-semibold tracking-tight">EquiSentinel</h1>
			<p class="text-muted text-sm">Real-time market monitor</p>
		</div>
		<div class="flex items-center gap-4">
			<div class="text-muted flex items-center gap-2 text-sm">
				<span class="h-2 w-2 rounded-full {statusMeta[socket.status].dot}"></span>
				{statusMeta[socket.status].label}
			</div>
			<ThemeToggle />
		</div>
	</header>

	<nav class="glass-panel flex flex-wrap gap-2 rounded-2xl p-2">
		{#each TICKERS as ticker (ticker)}
			<button
				type="button"
				onclick={() => (activeTicker = ticker)}
				class="rounded-xl px-4 py-2 text-sm font-medium transition {activeTicker === ticker
					? 'text-white'
					: 'text-muted hover:bg-black/5 dark:hover:bg-white/5'}"
				style={activeTicker === ticker
					? `background: linear-gradient(135deg, var(--accent), var(--accent-2));`
					: ''}
			>
				{ticker}
			</button>
		{/each}
	</nav>

	<section class="glass-panel flex flex-col gap-4 rounded-2xl p-6">
		<div class="flex items-baseline justify-between">
			<h2 class="text-2xl font-semibold">{activeTicker}</h2>
			{#if latestQuote}
				<span class="font-mono text-xl">{latestQuote.close.toLocaleString('id-ID')}</span>
			{/if}
		</div>
		<div class="h-[280px] sm:h-[320px]">
			<CandlestickChart ticker={activeTicker} />
		</div>
	</section>

	{#if latestAnalysis}
		<section class="glass-panel flex flex-col gap-3 rounded-2xl p-6">
			<div class="flex items-center justify-between">
				<h3 class="text-sm font-semibold tracking-tight">AI Analysis</h3>
				<div class="flex items-center gap-2">
					<span class="rounded-full px-3 py-1 text-xs font-medium {sentimentMeta[latestAnalysis.sentiment].class}">
						{sentimentMeta[latestAnalysis.sentiment].label}
					</span>
					<span class="rounded-full px-3 py-1 text-xs font-medium {riskMeta[latestAnalysis.riskLevel].class}">
						{riskMeta[latestAnalysis.riskLevel].label}
					</span>
				</div>
			</div>
			<p class="text-sm leading-relaxed">{latestAnalysis.summary}</p>
			<div class="flex items-center justify-between">
				<p class="text-muted text-xs">
					{latestAnalysis.modelUsed} &middot; {latestAnalysis.latencyMs}ms
				</p>
				<div class="flex items-center gap-2">
					<button
						type="button"
						disabled={submittingFeedback}
						onclick={() => submitFeedback('ACCURATE')}
						class="rounded-full px-3 py-1 text-xs font-medium transition disabled:opacity-50 {latestAnalysis.feedback ===
						'ACCURATE'
							? 'bg-emerald-500 text-white'
							: 'text-muted bg-black/5 hover:bg-emerald-500/15 dark:bg-white/5'}"
					>
						Akurat
					</button>
					<button
						type="button"
						disabled={submittingFeedback}
						onclick={() => submitFeedback('INACCURATE')}
						class="rounded-full px-3 py-1 text-xs font-medium transition disabled:opacity-50 {latestAnalysis.feedback ===
						'INACCURATE'
							? 'bg-rose-500 text-white'
							: 'text-muted bg-black/5 hover:bg-rose-500/15 dark:bg-white/5'}"
					>
						Tidak Akurat
					</button>
				</div>
			</div>
		</section>
	{/if}
</div>
