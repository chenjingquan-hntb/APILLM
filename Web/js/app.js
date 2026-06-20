/**
 * APILLM Frontend — Application Logic
 * 健康状态轮询 / 模型加载 / Chat Playground
 */
(function () {
  'use strict';

  // --- DOM 引用 ---
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        // Navbar
        baseUrlInput:   $('#base-url-input'),
        apiKeyInput:    $('#api-key-input'),
        apiKeyApplyBtn: $('#api-key-apply'),
        keyStatus:      $('#key-status'),

        // Health
        healthStatus:   $('#health-status'),
        healthRedis:    $('#health-redis'),
        healthDb:       $('#health-db'),
        healthUpstreams:$('#health-upstreams'),
        healthTime:     $('#health-time'),
        healthRefresh:  $('#health-refresh'),

        // Models
        modelCount:     $('#model-count'),
        modelGrid:      $('#model-grid'),
        modelLoadBtn:   $('#model-load'),
        modelStatus:    $('#model-status'),

    // Playground
    pgModel:        $('#pg-model'),
    pgMessages:     $('#pg-messages'),
    pgInput:        $('#pg-input'),
    pgSend:         $('#pg-send'),
    pgStream:       $('#pg-stream'),
    pgClear:        $('#pg-clear'),
    pgStatus:       $('#pg-status'),
  };

  // --- 状态 ---
  let healthTimer = null;
  let pgAbortController = null;

  // --- 初始化 ---
  function init() {
    // 恢复存储的配置
    dom.baseUrlInput.value = APILLM.getBaseUrl();
    dom.apiKeyInput.value = APILLM.getApiKey();
    updateKeyStatus();

    // 事件绑定
    dom.baseUrlInput.addEventListener('change', () => {
      APILLM.setBaseUrl(dom.baseUrlInput.value);
      refreshHealth();
    });

    dom.apiKeyApplyBtn.addEventListener('click', () => {
      APILLM.setApiKey(dom.apiKeyInput.value);
      updateKeyStatus();
      loadModels();
    });

    dom.apiKeyInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        APILLM.setApiKey(dom.apiKeyInput.value);
        updateKeyStatus();
        loadModels();
      }
    });

    dom.healthRefresh.addEventListener('click', refreshHealth);
    dom.modelLoadBtn.addEventListener('click', loadModels);

    dom.pgSend.addEventListener('click', sendMessage);
    dom.pgInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    dom.pgClear.addEventListener('click', clearChat);

    // 启动健康轮询 (30s)
    refreshHealth();
    healthTimer = setInterval(refreshHealth, 30000);

    // 如果有 API Key，自动加载模型
    if (APILLM.hasApiKey()) {
      loadModels();
    }
  }

  // --- API Key 状态 ---
  function updateKeyStatus() {
    if (APILLM.hasApiKey()) {
      dom.keyStatus.textContent = '✓ 已设置';
      dom.keyStatus.className = 'status-dot ok';
      dom.keyStatus.style.display = 'inline-flex';
      dom.keyStatus.style.alignItems = 'center';
      dom.keyStatus.style.gap = '0.375rem';
      dom.keyStatus.style.fontSize = '0.75rem';
      dom.keyStatus.style.color = 'var(--accent-green)';
    } else {
      dom.keyStatus.textContent = '○ 未设置';
      dom.keyStatus.className = 'status-dot warn';
      dom.keyStatus.style.display = 'inline-flex';
      dom.keyStatus.style.alignItems = 'center';
      dom.keyStatus.style.gap = '0.375rem';
      dom.keyStatus.style.fontSize = '0.75rem';
      dom.keyStatus.style.color = 'var(--accent-yellow)';
    }
  }

    // --- 健康检查 ---
    async function refreshHealth() {
        // Spinner animation
        dom.healthRefresh.classList.add('spinning');
        dom.healthRefresh.disabled = true;
        try {
            const data = await APILLM.health();
            updateHealthDisplay(data);
        } catch (e) {
            updateHealthDisplay({
                status: 'error',
                redis: 'unknown',
                db: 'unknown',
                upstreams: { total: 0, healthy: 0, degraded: 0, unhealthy: 0 },
            });
            console.error('Health check failed:', e.message);
        } finally {
            dom.healthRefresh.classList.remove('spinning');
            dom.healthRefresh.disabled = false;
            dom.healthTime.textContent = new Date().toLocaleTimeString();
        }
    }

    function updateHealthDisplay(data) {
        const statusClass = data.status === 'ok' ? 'ok' : (data.status === 'degraded' ? 'warn' : 'error');
        const statusText = data.status === 'ok' ? '正常' : (data.status === 'degraded' ? '降级' : '异常');

        dom.healthStatus.innerHTML = `<span class="status-dot ${statusClass}"></span>${statusText}`;
        dom.healthStatus.style.display = 'inline-flex';
        dom.healthStatus.style.alignItems = 'center';

        dom.healthRedis.innerHTML = `<span class="status-dot ${data.redis === 'ok' ? 'ok' : 'error'}"></span>Redis: ${data.redis}`;
        dom.healthRedis.style.display = 'inline-flex';
        dom.healthRedis.style.alignItems = 'center';

        dom.healthDb.innerHTML = `<span class="status-dot ${data.db === 'ok' ? 'ok' : 'error'}"></span>DB: ${data.db}`;
        dom.healthDb.style.display = 'inline-flex';
        dom.healthDb.style.alignItems = 'center';

        // Upstream summary
        const us = data.upstreams;
        if (us && dom.healthUpstreams) {
            const parts = [];
            if (us.healthy > 0) parts.push(`<span class="status-dot ok"></span>正常 ${us.healthy}`);
            if (us.degraded > 0) parts.push(`<span class="status-dot warn"></span>降级 ${us.degraded}`);
            if (us.unhealthy > 0) parts.push(`<span class="status-dot error"></span>异常 ${us.unhealthy}`);
            dom.healthUpstreams.innerHTML = `上游 (${us.total}): ${parts.join('&nbsp;&nbsp;') || '无'}`;
            dom.healthUpstreams.style.display = 'inline-flex';
            dom.healthUpstreams.style.alignItems = 'center';
            dom.healthUpstreams.style.gap = '0.25rem';
            dom.healthUpstreams.style.fontSize = '0.8125rem';
            dom.healthUpstreams.style.color = 'var(--text-secondary)';
        }
    }

  // --- 模型列表 ---
  async function loadModels() {
    if (!APILLM.hasApiKey()) {
      dom.modelStatus.textContent = '请先设置 API Key';
      dom.modelStatus.style.color = 'var(--accent-yellow)';
      return;
    }
    dom.modelStatus.textContent = '加载中...';
    dom.modelStatus.style.color = 'var(--text-secondary)';
    dom.modelLoadBtn.disabled = true;

    try {
      const data = await APILLM.listModels();
      renderModels(data.data || []);
      dom.modelStatus.textContent = '';
    } catch (e) {
      dom.modelStatus.textContent = `加载失败: ${e.message}`;
      dom.modelStatus.style.color = 'var(--accent-red)';
      dom.modelGrid.innerHTML = '';
      dom.modelCount.textContent = '0';
    } finally {
      dom.modelLoadBtn.disabled = false;
    }
  }

    function renderModels(models) {
        dom.modelCount.textContent = models.length;
        if (models.length === 0) {
            dom.modelGrid.innerHTML = '<div class="message system">暂无可用模型</div>';
            return;
        }
        dom.modelGrid.innerHTML = models
            .map((m) => {
                const priceStr = m.lowest_price != null
                    ? `¥${(m.lowest_price * 1000).toFixed(2)}/Kt`
                    : '价格未知';
                const availClass = m.available ? 'model-available' : 'model-unavailable';
                const availText = m.available ? '' : ' (不可用)';
                const title = `${m.id}\n${priceStr}${availText}\n来源: ${m.upstream_count || 1} 个上游`;
                return `<div class="model-tag ${availClass}" title="${title.replace(/"/g, '&quot;')}">
                    <span class="model-tag-name">${m.id}</span>
                    <span class="model-tag-price">${priceStr}</span>
                    <span class="model-tag-count">×${m.upstream_count || 1}</span>
                </div>`;
            })
            .join('');

        // 更新 Playground 模型下拉
        const current = dom.pgModel.value;
        dom.pgModel.innerHTML = models
            .map((m) => `<option value="${m.id}" ${m.id === current ? 'selected' : ''}>${m.id}</option>`)
            .join('');
        if (!current && models.length > 0) {
            dom.pgModel.value = models[0].id;
        }
    }

  // --- Chat Playground ---
  async function sendMessage() {
    const content = dom.pgInput.value.trim();
    if (!content) return;

    if (!APILLM.hasApiKey()) {
      addMessage('system', '请先设置 API Key');
      return;
    }

    const model = dom.pgModel.value;
    const stream = dom.pgStream.checked;

    // 显示用户消息
    addMessage('user', content);
    dom.pgInput.value = '';
    dom.pgSend.disabled = true;
    dom.pgStatus.textContent = stream ? '流式传输中...' : '请求中...';

    if (pgAbortController) {
      pgAbortController.abort();
    }
    pgAbortController = new AbortController();

    // 助手消息占位
    const assistantMsgEl = addMessage('assistant', stream ? '' : '思考中...');
    let fullContent = '';

    try {
      if (stream) {
        await APILLM.chatCompletionStream(
          {
            model,
            messages: [{ role: 'user', content }],
          },
          (chunk) => {
            const delta = chunk.choices?.[0]?.delta?.content;
            if (delta) {
              fullContent += delta;
              assistantMsgEl.textContent = fullContent;
            }
          },
          () => {
            if (!fullContent) {
              assistantMsgEl.textContent = '(空响应)';
            }
            dom.pgStatus.textContent = '完成';
          },
          (err) => {
            assistantMsgEl.textContent = `流式错误: ${err.message}`;
            assistantMsgEl.className = 'message system';
            dom.pgStatus.textContent = '错误';
          },
          pgAbortController.signal,
        );
      } else {
        const data = await APILLM.chatCompletion(
          {
            model,
            messages: [{ role: 'user', content }],
          },
          pgAbortController.signal,
        );
        fullContent = data.choices?.[0]?.message?.content || '(空响应)';
        assistantMsgEl.textContent = fullContent;
        dom.pgStatus.textContent = '完成';
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        assistantMsgEl.textContent = `错误: ${e.message}`;
        assistantMsgEl.className = 'message system';
        dom.pgStatus.textContent = '错误';
      }
    } finally {
      dom.pgSend.disabled = false;
      pgAbortController = null;
      // 滚动到底
      dom.pgMessages.scrollTop = dom.pgMessages.scrollHeight;
    }
  }

  function addMessage(role, content) {
    const el = document.createElement('div');
    el.className = `message ${role}`;
    el.textContent = content;
    dom.pgMessages.appendChild(el);
    dom.pgMessages.scrollTop = dom.pgMessages.scrollHeight;
    return el;
  }

  function clearChat() {
    dom.pgMessages.innerHTML = '';
    addMessage('system', '在下方输入消息，测试 API 中转功能');
  }

  // --- 启动 ---
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
