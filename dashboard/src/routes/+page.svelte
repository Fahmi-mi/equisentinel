<script lang="ts">
	import { onMount } from 'svelte';
	import { GatewaySocket } from '$lib/ws/client.svelte';
	import { quoteStore } from '$lib/stores/quotes.svelte';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';
	import CandlestickChart from '$lib/components/CandlestickChart.svelte';

	const TICKERS = ['BBCA', 'BBRI', 'TLKM', 'ASII', 'GOTO'];
	const GATEWAY_WS_URL = import.meta.env.VITE_GATEWAY_WS_URL ?? 'ws://localhost:8080/ws';

	let activeTicker = $state(TICKERS[0]);
	const socket = new GatewaySocket(GATEWAY_WS_URL);

	onMount(() => {
		socket.connect();
		return () => socket.disconnect();
	});

	const statusMeta = {
		connecting: { label: 'Connecting…', dot: 'bg-amber-400' },
		open: { label: 'Live', dot: 'bg-emerald-400' },
		closed: { label: 'Disconnected', dot: 'bg-rose-400' }
	} as const;

	const latestQuote = $derived(quoteStore.latest(activeTicker).at(-1));
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
</div>
