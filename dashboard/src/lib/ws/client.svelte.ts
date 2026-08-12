import { parseGatewayMessage } from './parse';
import { quoteStore } from '$lib/stores/quotes.svelte';
import { analysisStore } from '$lib/stores/analyses.svelte';

const RECONNECT_DELAY_MS = 2000;

export type ConnectionStatus = 'connecting' | 'open' | 'closed';

export class GatewaySocket {
	status = $state<ConnectionStatus>('connecting');

	private url: string;
	private socket: WebSocket | null = null;
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	private closedByUser = false;

	constructor(url: string) {
		this.url = url;
	}

	connect() {
		this.closedByUser = false;
		this.status = 'connecting';

		const socket = new WebSocket(this.url);
		this.socket = socket;

		socket.addEventListener('open', () => {
			this.status = 'open';
		});

		socket.addEventListener('message', (event) => {
			try {
				const message = parseGatewayMessage(event.data);
				if (message.type === 'quote') {
					quoteStore.add(message.quote);
				} else {
					const { analysis } = message;
					const time =
						quoteStore.latest(analysis.ticker).at(-1)?.time ?? Math.floor(Date.now() / 1000);
					analysisStore.add({ ...analysis, time });
				}
			} catch (err) {
				console.error('failed to parse gateway message', err);
			}
		});

		socket.addEventListener('close', () => {
			this.status = 'closed';
			if (!this.closedByUser) this.scheduleReconnect();
		});

		socket.addEventListener('error', () => {
			socket.close();
		});
	}

	disconnect() {
		this.closedByUser = true;
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		this.socket?.close();
	}

	private scheduleReconnect() {
		if (this.reconnectTimer) return;
		this.reconnectTimer = setTimeout(() => {
			this.reconnectTimer = null;
			this.connect();
		}, RECONNECT_DELAY_MS);
	}
}
