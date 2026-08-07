<script lang="ts">
	import { themeStore } from '$lib/stores/theme.svelte';
</script>

<button
	type="button"
	onclick={() => themeStore.toggle()}
	class="glass-panel flex h-10 w-10 items-center justify-center rounded-full transition hover:scale-105"
	aria-label="Toggle color theme"
>
	{#if themeStore.current === 'dark'}
		<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" class="h-5 w-5">
			<circle cx="12" cy="12" r="4.5" />
			<path stroke-linecap="round" d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
		</svg>
	{:else}
		<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5">
			<path d="M20.2 14.9A8.5 8.5 0 1 1 9.1 3.8a7 7 0 0 0 11.1 11.1Z" />
		</svg>
	{/if}
</button>
