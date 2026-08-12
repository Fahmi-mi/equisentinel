import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const GATEWAY_HTTP_URL = env.GATEWAY_HTTP_URL ?? 'http://localhost:8080';

export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = await request.json();

	const res = await fetch(`${GATEWAY_HTTP_URL}/feedback`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		return json({ error: 'failed to submit feedback' }, { status: res.status });
	}

	return json({ status: 'ok' });
};
