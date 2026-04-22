import { Platform } from 'react-native';
import Constants from 'expo-constants';

function resolveExpoHostIp(): string | null {
  const hostUri =
    Constants.expoConfig?.hostUri ??
    (Constants as any).expoGoConfig?.debuggerHost ??
    (Constants as any).manifest2?.extra?.expoGo?.debuggerHost;

  if (!hostUri || typeof hostUri !== 'string') {
    return null;
  }

  const [host] = hostUri.split(':');
  return host || null;
}

const expoHostIp = resolveExpoHostIp();

const defaultBaseUrl = Platform.select({
  ios: 'http://localhost:8000',
  android: expoHostIp ? `http://${expoHostIp}:8000` : 'http://10.0.2.2:8000',
  web: 'http://127.0.0.1:8000',
  default: 'http://localhost:8000',
});

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? defaultBaseUrl ?? 'http://localhost:8000';

export const API_FALLBACK_BASE_URLS =
  Platform.OS === 'web'
    ? Array.from(new Set([API_BASE_URL, 'http://127.0.0.1:8000', 'http://localhost:8000']))
    : [API_BASE_URL];
