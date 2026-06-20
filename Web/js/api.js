/**
 * APILLM Frontend — API Client
 * 封装与后端 API 的交互，处理认证、错误、流式响应
 */
const APILLM = (() => {
  // --- 配置 ---
  let baseUrl = localStorage.getItem('apillm_base_url') || 'http://127.0.0.1:8000';
  let apiKey = localStorage.getItem('apillm_api_key') || '';

  // --- 工具函数 ---
  function headers(auth = true) {
    const h = { 'Content-Type': 'application/json' };
    if (auth && apiKey) {
      h['Authorization'] = `Bearer ${apiKey}`;
    }
    return h;
  }

  async function request(method, path, options = {}) {
    const { auth = true, body, signal } = options;
    const url = `${baseUrl}${path}`;
    const fetchOptions = {
      method,
      headers: headers(auth),
      signal,
    };
    if (body) {
      fetchOptions.body = JSON.stringify(body);
    }
    const resp = await fetch(url, fetchOptions);
    if (!resp.ok) {
      const text = await resp.text().catch(() => 'Unknown error');
      let detail = text;
      try { detail = JSON.parse(text).detail || text; } catch (_) { /* raw text */ }
      throw new Error(`[${resp.status}] ${detail}`);
    }
    return resp;
  }

  // --- API 方法 ---
  return {
    /** 设置基础 URL */
    setBaseUrl(url) {
      baseUrl = url.replace(/\/+$/, '');
      localStorage.setItem('apillm_base_url', baseUrl);
    },
    getBaseUrl() { return baseUrl; },

    /** 设置 API Key */
    setApiKey(key) {
      apiKey = key.trim();
      localStorage.setItem('apillm_api_key', apiKey);
    },
    getApiKey() { return apiKey; },
    hasApiKey() { return apiKey.length > 0; },

    /** GET /health — 无需认证 */
    async health() {
      const resp = await request('GET', '/health', { auth: false });
      return resp.json();
    },

    /** GET /v1/models — 需要认证 */
    async listModels(signal) {
      const resp = await request('GET', '/v1/models', { signal });
      return resp.json();
    },

    /** POST /v1/chat/completions — 非流式 */
    async chatCompletion(body, signal) {
      const resp = await request('POST', '/v1/chat/completions', { body, signal });
      return resp.json();
    },

    /** POST /v1/chat/completions — 流式 (SSE) */
    async chatCompletionStream(body, onChunk, onDone, onError, signal) {
      const url = `${baseUrl}/v1/chat/completions`;
      const fetchOptions = {
        method: 'POST',
        headers: headers(true),
        body: JSON.stringify({ ...body, stream: true }),
        signal,
      };
      try {
        const resp = await fetch(url, fetchOptions);
        if (!resp.ok) {
          const text = await resp.text().catch(() => 'Unknown error');
          let detail = text;
          try { detail = JSON.parse(text).detail || text; } catch (_) { /* raw */ }
          throw new Error(`[${resp.status}] ${detail}`);
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 保留不完整行
          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data: ')) continue;
            const data = trimmed.slice(6);
            if (data === '[DONE]') {
              onDone && onDone();
              return;
            }
            try {
              const parsed = JSON.parse(data);
              onChunk && onChunk(parsed);
            } catch (_) {
              // 非 JSON 消息（如错误文本），跳过
            }
          }
        }
        onDone && onDone();
      } catch (e) {
        if (e.name !== 'AbortError') {
          onError && onError(e);
        }
      }
    },
  };
})();
