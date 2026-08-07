import { parseQuoteMessage } from './parse';
import { quoteStore } from '$lib/stores/quotes.svelte';

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
				quoteStore.add(parseQuoteMessage(event.data));
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
