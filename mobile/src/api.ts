/**
 * API service for communicating with the Flask backend server.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'SERVER_URL';
const DEFAULT_URL = 'http://192.168.1.100:5000';

export async function getServerUrl(): Promise<string> {
  const url = await AsyncStorage.getItem(STORAGE_KEY);
  return url || DEFAULT_URL;
}

export async function setServerUrl(url: string): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, url);
}

async function apiCall(path: string, options?: RequestInit) {
  const baseUrl = await getServerUrl();
  const res = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  });
  return res.json();
}

export const api = {
  getStatus: () => apiCall('/api/status'),

  startBot: (groupUrls: string[], maxPosts: number, delay: number) =>
    apiCall('/api/start', {
      method: 'POST',
      body: JSON.stringify({ group_urls: groupUrls, max_posts: maxPosts, delay }),
    }),

  stopBot: () => apiCall('/api/stop', { method: 'POST' }),

  getGroups: () => apiCall('/api/groups'),
  saveGroups: (groups: string[]) =>
    apiCall('/api/groups', { method: 'POST', body: JSON.stringify({ groups }) }),

  getComments: () => apiCall('/api/comments'),
  saveComments: (comments: string[]) =>
    apiCall('/api/comments', { method: 'POST', body: JSON.stringify({ comments }) }),

  getLogs: () => apiCall('/api/logs'),
};
