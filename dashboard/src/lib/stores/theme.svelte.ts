export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'equisentinel-theme';

function readStoredTheme(): Theme | null {
	const stored = localStorage.getItem(STORAGE_KEY);
	return stored === 'light' || stored === 'dark' ? stored : null;
}

function readPreferredTheme(): Theme {
	return readStoredTheme() ?? (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
}

class ThemeStore {
	current = $state<Theme>('dark');

	init() {
		this.current = readPreferredTheme();
		this.apply();
	}

	toggle() {
		this.current = this.current === 'dark' ? 'light' : 'dark';
		localStorage.setItem(STORAGE_KEY, this.current);
		this.apply();
	}

	private apply() {
		document.documentElement.dataset.theme = this.current;
	}
}

export const themeStore = new ThemeStore();
