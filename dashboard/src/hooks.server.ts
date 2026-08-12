import pino from 'pino';
import type { Handle } from '@sveltejs/kit';

const logger = pino({ level: process.env.NODE_ENV === 'production' ? 'info' : 'debug' });

export const handle: Handle = async ({ event, resolve }) => {
	const start = Date.now();
	const response = await resolve(event);

	logger.info({
		method: event.request.method,
		path: event.url.pathname,
		status: response.status,
		durationMs: Date.now() - start
	});

	return response;
};
