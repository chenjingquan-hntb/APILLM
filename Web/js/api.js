/**
 * APILLM Frontend — API Client
 * 封装 fetch 调用，处理 JWT / API Key 双认证
 */
(function () {
  'use strict';

  const LS_BASE_URL = 'apillm_base_url';
  const LS_API_KEY = 'apillm_api_key';
  const LS_TOKEN = 'apillm_token';
  const LS_USER = 'apillm_user';

  function getBaseUrl() {
    return localStorage.getItem(LS_BASE_URL) || window.location.origin;
  }

  function setBaseUrl(url) {
    localStorage.setItem(LS_BASE_URL, url);
  }

  function getApiKey() {
    return localStorage.getItem(LS_API_KEY) || '';
  }

  function setApiKey(key) {
    localStorage.setItem(LS_API_KEY, key);
  }

  function hasApiKey() {
    return !!getApiKey();
  }

  function getToken() {
    return localStorage.getItem(LS_TOKEN) || '';
  }

  function setToken(token) {
    localStorage.setItem(LS_TOKEN, token);
  }

  function getUser() {
    try {
      return JSON.parse(localStorage.getItem(LS_USER) || 'null');
    } catch { return null; }
  }

  function setUser(user) {
    localStorage.setItem(LS_USER, JSON.stringify(user));
  }

  function clearAuth() {
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem(LS_USER);
  }

  // ============================================================
  // 通用 fetch 封装
  // ============================================================
  async function request(path, options = {}) {
    const base = getBaseUrl();
    const url = `${base}${path}`;
    const token = getToken();

    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    } else if (getApiKey()) {
      headers['Authorization'] = `Bearer ${getApiKey()}`;
    }

    const res = await fetch(url, {
      ...options,
      headers,
      signal: options.signal,
    });

    if (res.status === 401) {
      clearAuth();
    }

    if (!res.ok) {
      let msg = res.statusText;
      try {
        const body = await res.json();
        msg = body.detail || body.message || msg;
      } catch {}
      throw new Error(msg);
    }

    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      return res.json();
    }
    return res;
  }

  // ============================================================
  // 公共 API
  // ============================================================
  async function health() {
    return request('/health');
  }

  async function listModels() {
    const apiKey = getApiKey();
    if (!apiKey && !getToken()) {
      throw new Error('请先登录或设置 API Key');
    }
    return request('/v1/models');
  }

  // Chat (SSE / non-stream)
  async function* chatStream(model, messages) {
    const base = getBaseUrl();
    const token = getToken();
    const apiKey = getApiKey();
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token || apiKey}`,
    };
    const res = await fetch(`${base}/v1/chat/completions`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ model, messages, stream: true }),
    });
    if (!res.ok) {
      let msg = res.statusText;
      try { const b = await res.json(); msg = b.detail || msg; } catch {}
      throw new Error(msg);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop() || '';
      for (const line of lines) {
        const t = line.trim();
        if (t.startsWith('data: ')) {
          const d = t.slice(6);
          if (d === '[DONE]') return;
          try { yield JSON.parse(d); } catch {}
        }
      }
    }
  }

  // ============================================================
  // Auth API
  // ============================================================
  async function login(username, password) {
    const data = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    setToken(data.access_token);
    localStorage.setItem('apillm_refresh', data.refresh_token);
    return data;
  }

  async function refreshToken() {
    const refresh = localStorage.getItem('apillm_refresh');
    if (!refresh) throw new Error('No refresh token');
    const data = await request('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refresh }),
    });
    setToken(data.access_token);
    localStorage.setItem('apillm_refresh', data.refresh_token);
    return data;
  }

  async function logout() {
    const refresh = localStorage.getItem('apillm_refresh');
    if (refresh) {
      try {
        await request('/api/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: refresh }),
        });
      } catch {}
    }
    clearAuth();
    localStorage.removeItem('apillm_refresh');
  }

  async function fetchMe() {
    const data = await request('/api/auth/me');
    setUser(data);
    return data;
  }

  // ============================================================
  // Admin API
  // ============================================================
  async function adminListUpstreams() {
    return request('/api/admin/upstreams');
  }
  async function adminCreateUpstream(data) {
    return request('/api/admin/upstreams', { method: 'POST', body: JSON.stringify(data) });
  }
  async function adminUpdateUpstream(id, data) {
    return request(`/api/admin/upstreams/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  }
  async function adminDeleteUpstream(id) {
    return request(`/api/admin/upstreams/${id}`, { method: 'DELETE' });
  }

  async function adminListModels() {
    return request('/api/admin/models');
  }
  async function adminCreateModel(data) {
    return request('/api/admin/models', { method: 'POST', body: JSON.stringify(data) });
  }
  async function adminUpdateModel(id, data) {
    return request(`/api/admin/models/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  }
  async function adminDeleteModel(id) {
    return request(`/api/admin/models/${id}`, { method: 'DELETE' });
  }

  async function adminListUsers() {
    return request('/api/admin/users');
  }
  async function adminCreateUser(data) {
    return request('/api/admin/users', { method: 'POST', body: JSON.stringify(data) });
  }
  async function adminUpdateUser(id, data) {
    return request(`/api/admin/users/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  }
  async function adminDeleteUser(id) {
    return request(`/api/admin/users/${id}`, { method: 'DELETE' });
  }

  async function adminPriceFetch() {
    return request('/api/admin/prices/fetch', { method: 'POST' });
  }
  async function adminHealthCheck() {
    return request('/api/admin/health/check', { method: 'POST' });
  }

  // User API
  async function userListKeys() {
    return request('/api/user/keys');
  }
  async function userCreateKey(label) {
    return request('/api/user/keys', { method: 'POST', body: JSON.stringify({ label }) });
  }
  async function userDeleteKey(id) {
    return request(`/api/user/keys/${id}`, { method: 'DELETE' });
  }
  async function userListLogs(page = 1, size = 20) {
    return request(`/api/user/logs?page=${page}&size=${size}`);
  }
  async function userStats() {
    return request('/api/user/stats');
  }

  // Admin logs & stats
  async function adminListLogs(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return request(`/api/admin/logs${qs ? '?' + qs : ''}`);
  }
  async function adminStatsOverview() {
    return request('/api/admin/stats/overview');
  }
  async function adminStatsByModel() {
    return request('/api/admin/stats/by-model');
  }
  async function adminStatsByUpstream() {
    return request('/api/admin/stats/by-upstream');
  }

  // ============================================================
  // 导出
  // ============================================================
  window.APILLM = {
    // Config
    getBaseUrl, setBaseUrl,
    getApiKey, setApiKey, hasApiKey,
    // Auth
    getToken, setToken, getUser, setUser, clearAuth,
    login, refreshToken, logout, fetchMe,
    // API
    request,
    health,
    listModels,
    chatStream,
    // User
    userListKeys, userCreateKey, userDeleteKey,
    userListLogs, userStats,
    // Admin
    adminListUpstreams, adminCreateUpstream, adminUpdateUpstream, adminDeleteUpstream,
    adminListModels, adminCreateModel, adminUpdateModel, adminDeleteModel,
    adminListUsers, adminCreateUser, adminUpdateUser, adminDeleteUser,
    adminPriceFetch, adminHealthCheck,
    adminListLogs, adminStatsOverview, adminStatsByModel, adminStatsByUpstream,
  };
})();
