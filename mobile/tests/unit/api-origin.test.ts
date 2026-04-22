vi.mock('react-native', () => ({
  Platform: {
    OS: 'android',
    select: (values: Record<string, string>) => values.android ?? values.default,
  },
}));

vi.mock('expo-constants', () => ({
  default: {
    expoConfig: null,
  },
}));

import {
  clearApiBaseUrlOverride,
  getApiBaseUrl,
  normalizeApiBaseUrl,
  setApiBaseUrlOverride,
} from '../../src/config/env';
import { requestJson } from '../../src/lib/http';

describe('API origin configuration', () => {
  beforeEach(() => {
    clearApiBaseUrlOverride();
    vi.restoreAllMocks();
  });

  it('normalizes API origins for stable request building', () => {
    expect(normalizeApiBaseUrl(' https://api.example.com/rps/// ')).toBe('https://api.example.com/rps');
    expect(() => normalizeApiBaseUrl('api.example.com')).toThrow('http:// or https://');
  });

  it('uses the runtime API origin override for relative API calls', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ session_id: 'abc', max_rounds: 5 }),
    }));
    vi.stubGlobal('fetch', fetchMock);

    setApiBaseUrlOverride('https://backend.example.com/game-api/');

    const data = await requestJson('/sessions', { method: 'POST', body: {} });

    expect(getApiBaseUrl()).toBe('https://backend.example.com/game-api');
    expect(data).toEqual({ session_id: 'abc', max_rounds: 5 });
    expect(fetchMock).toHaveBeenCalledWith(
      'https://backend.example.com/game-api/sessions',
      expect.objectContaining({
        method: 'POST',
      }),
    );
  });
});
