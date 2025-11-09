import axios from 'axios';

const DEFAULT_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';
export const API_BASE_URL = DEFAULT_BASE_URL.replace(/\/$/, '');

const api = axios.create({
  baseURL: API_BASE_URL
});

export default api;
