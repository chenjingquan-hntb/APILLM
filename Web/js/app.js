/**
 * APILLM Frontend — Application Logic
 * 路由 / 视图切换 / 交互逻辑
 */
(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ============================================================
  // 状态
  // ============================================================
  let healthTimer = null;
  let currentView = 'home';

  // ============================================================
  // 初始化
  // ============================================================
  function init() {
    // 导航点击
    $$('#app-nav .nav-link').forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        navigateTo(link.getAttribute('href').slice(1));
      });
    });

    // 登录按钮
    $('#btn-login-go').addEventListener('click', () => navigateTo('login'));
    $('#btn-logout').addEventListener('click', doLogout);
    $('#btn-login').addEventListener('click', doLogin);

    // 键盘登录
    $('#login-password').addEventListener('keydown', e => {
      if (e.key === 'Enter') doLogin();
    });

    // 健康刷新
    $('#hb-refresh').addEventListener('click', refreshHealth);
    $('#btn-load-models').addEventListener('click', () => {
      loadModels();
    });

    // 检查登录状态
    checkAuth().then(() => {
      // 根据 hash 或默认路由导航
      const hash = window.location.hash.slice(1) || 'home';
      navigateTo(hash);
    });

    // hash 变化监听
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.slice(1) || 'home';
      navigateTo(hash);
    });

    // 健康轮询
    refreshHealth();
    healthTimer = setInterval(refreshHealth, 30000);
  }

  // ============================================================
  // 路由
  // ============================================================
  async function navigateTo(view) {
    currentView = view;

    // 检查权限
    const user = APILLM.getUser();
    if ((view === 'admin') && (!user || user.role !== 'admin')) {
      view = 'home';
    }
    if ((view === 'user') && !user) {
      view = 'login';
    }

    // 更新 URL hash
    if (window.location.hash.slice(1) !== view) {
      window.location.hash = view;
    }

    // 切换视图
    $$('.view').forEach(v => v.classList.remove('active'));
    const target = $(`#view-${view}`);
    if (target) target.classList.add('active');

    // 更新顶栏
    updateNav(view);

    // 加载视图数据
    switch (view) {
      case 'home':
        loadModels();
        break;
      case 'admin':
        initAdminTabs();
        loadAdminUpstreams();
        break;
      case 'user':
        initUserTabs();
        loadUserKeys();
        break;
    }
  }

  function updateNav(current) {
    $$('#app-nav .nav-link').forEach(l => l.classList.remove('active'));
    const activeLink = $(`#app-nav a[href="#${current}"]`);
    if (activeLink) activeLink.classList.add('active');

    const user = APILLM.getUser();
    const token = APILLM.getToken();
    if (token && user) {
      $('#btn-login-go').style.display = 'none';
      $('#user-info').style.display = '';
      $('#user-name').textContent = user.username;
      // 角色相关导航
      $$('.nav-user-only').forEach(el => el.style.display = '');
      if (user.role === 'admin') {
        $$('.nav-admin-only').forEach(el => el.style.display = '');
      }
    } else {
      $('#btn-login-go').style.display = '';
      $('#user-info').style.display = 'none';
      $$('.nav-user-only').forEach(el => el.style.display = 'none');
      $$('.nav-admin-only').forEach(el => el.style.display = 'none');
    }
  }

  async function checkAuth() {
    const token = APILLM.getToken();
    if (!token) return;
    try {
      const user = await APILLM.fetchMe();
      updateNav(currentView);
    } catch {
      // Try refresh
      try {
        await APILLM.refreshToken();
        const user = await APILLM.fetchMe();
        updateNav(currentView);
      } catch {
        APILLM.clearAuth();
      }
    }
  }

  // ============================================================
  // 健康检查
  // ============================================================
  async function refreshHealth() {
    const btn = $('#hb-refresh');
    btn.classList.add('spinning');
    try {
      const data = await APILLM.health();
      renderHealth(data);
    } catch {
      $('#hb-status').innerHTML = '<span class="dot error"></span>异常';
    } finally {
      btn.classList.remove('spinning');
      $('#hb-time').textContent = new Date().toLocaleTimeString();
    }
  }

  function renderHealth(data) {
    const cls = data.status === 'ok' ? 'ok' : 'warn';
    $('#hb-status').innerHTML = `<span class="dot ${cls}"></span>${data.status === 'ok' ? '正常' : '降级'}`;
    const us = data.upstreams;
    if (us) {
      const parts = [];
      if (us.healthy > 0) parts.push(`${us.healthy}<span class="dot ok"></span>`);
      if (us.degraded > 0) parts.push(`${us.degraded}<span class="dot warn"></span>`);
      if (us.unhealthy > 0) parts.push(`${us.unhealthy}<span class="dot error"></span>`);
      $('#hb-upstreams').innerHTML = `上游: ${us.total} | ${parts.join(' ')}`;
    }
  }

  // ============================================================
  // 模型列表 (首页)
  // ============================================================
  async function loadModels() {
    const grid = $('#model-card-grid');
    grid.innerHTML = '<div class="message">加载中…</div>';
    try {
      const data = await APILLM.listModels();
      renderModelCards(data.data || []);
    } catch (e) {
      grid.innerHTML = `<div class="message error">加载失败: ${e.message}</div>`;
    }
  }

  function renderModelCards(models) {
    const grid = $('#model-card-grid');
    if (!models.length) {
      grid.innerHTML = '<div class="message">暂无模型</div>';
      return;
    }
    grid.innerHTML = models.map(m => {
      const priceStr = m.lowest_price != null
        ? `¥${(m.lowest_price * 1000).toFixed(3)}/Kt`
        : '暂无报价';
      const availClass = m.available ? 'card-ok' : 'card-err';
      return `
        <div class="model-card ${availClass}">
          <div class="card-head">
            <span class="card-model-name">${esc(m.id)}</span>
            <span class="card-upstreams">${m.upstream_count || 1}源</span>
          </div>
          <div class="card-price">${priceStr}</div>
          <div class="card-foot">
            <span class="card-avail">${m.available ? '✓ 可用' : '✗ 不可用'}</span>
          </div>
        </div>`;
    }).join('');
  }

  // ============================================================
  // 登录
  // ============================================================
  async function doLogin() {
    const username = $('#login-username').value.trim();
    const password = $('#login-password').value;
    const errEl = $('#login-error');
    if (!username || !password) {
      errEl.textContent = '请输入用户名和密码';
      errEl.style.display = '';
      return;
    }
    errEl.style.display = 'none';
    try {
      await APILLM.login(username, password);
      await APILLM.fetchMe();
      navigateTo('home');
    } catch (e) {
      errEl.textContent = e.message || '登录失败';
      errEl.style.display = '';
    }
  }

  async function doLogout() {
    await APILLM.logout();
    navigateTo('home');
  }

  // ============================================================
  // 管理后台
  // ============================================================
  function initAdminTabs() {
    $$('#admin-tabs .tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        $$('#admin-tabs .tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        $$('#view-admin .tab-panel').forEach(p => p.classList.remove('active'));
        $(`#admin-tab-${tabName}`).classList.add('active');
        if (tabName === 'upstreams') loadAdminUpstreams();
        if (tabName === 'models') loadAdminModels();
        if (tabName === 'users') loadAdminUsers();
        if (tabName === 'stats') loadAdminStats();
      });
    });
    $('#btn-upstream-add').addEventListener('click', () => openUpstreamForm());
    $('#btn-model-add').addEventListener('click', () => openModelForm());
    $('#btn-user-add').addEventListener('click', () => openUserForm());
    $('#btn-price-fetch').addEventListener('click', async () => {
      try { await APILLM.adminPriceFetch(); alert('价格抓取已触发'); } catch(e) { alert('失败: ' + e.message); }
    });
    $('#btn-health-check').addEventListener('click', async () => {
      try { await APILLM.adminHealthCheck(); alert('健康检查已触发'); } catch(e) { alert('失败: ' + e.message); }
    });
    $$('#admin-tab-stats .toolbar button').forEach(btn => {
      btn.addEventListener('click', () => loadAdminStats(btn.textContent.includes('模型') ? 'models' : 'upstreams'));
    });
  }

  // ---------- 上游管理 ----------
  async function loadAdminUpstreams() {
    try {
      const data = await APILLM.adminListUpstreams();
      const tbody = $('#table-upstreams tbody');
      tbody.innerHTML = data.map(u => `
        <tr>
          <td>${esc(u.name)}</td>
          <td>${u.protocol}</td>
          <td><code>${esc(u.base_url.slice(0,40))}…</code></td>
          <td><span class="dot ${u.is_enabled ? 'ok' : 'error'}"></span>${u.is_enabled ? '启用' : '禁用'}</td>
          <td class="actions">
            <button class="btn-text" onclick="window._adminEditUpstream(${u.id})">编辑</button>
            <button class="btn-text danger" onclick="window._adminDelUpstream(${u.id})">删除</button>
          </td>
        </tr>`).join('');
    } catch (e) { console.error(e); }
  }

  window._adminEditUpstream = (id) => openUpstreamForm(id);
  window._adminDelUpstream = async (id) => {
    if (!confirm('确定删除此上游？')) return;
    try { await APILLM.adminDeleteUpstream(id); loadAdminUpstreams(); } catch(e) { alert(e.message); }
  };

  function openUpstreamForm(id) {
    const title = id ? '编辑上游' : '新增上游';
    const body = `
      <div class="form-group"><label>名称</label><input id="uf-name" class="input"></div>
      <div class="form-group"><label>地址</label><input id="uf-url" class="input" placeholder="https://api.openai.com"></div>
      <div class="form-group"><label>API Key</label><input id="uf-key" class="input" type="password"></div>
      <div class="form-group"><label>协议</label><select id="uf-proto" class="input"><option value="openai">openai</option><option value="anthropic">anthropic</option></select></div>
      <div class="form-group"><label>加价率</label><input id="uf-markup" class="input" type="number" step="0.01" value="0.2"></div>
      <button class="btn primary" id="uf-submit" style="width:100%">保存</button>
    `;
    openModal(title, body, async () => {
      const data = {
        name: $('#uf-name').value, base_url: $('#uf-url').value, api_key: $('#uf-key').value,
        protocol: $('#uf-proto').value, markup_rate: parseFloat($('#uf-markup').value) || 0.2,
      };
      if (id) await APILLM.adminUpdateUpstream(id, data);
      else await APILLM.adminCreateUpstream(data);
      loadAdminUpstreams();
    });
  }

  // ---------- 模型配置 ----------
  async function loadAdminModels() {
    try {
      const data = await APILLM.adminListModels();
      const tbody = $('#table-models tbody');
      tbody.innerHTML = data.map(m => `
        <tr>
          <td><code>${esc(m.model_id)}</code></td>
          <td>${esc(m.display_name || '—')}</td>
          <td>${m.manual_prompt_price != null ? '¥'+(m.manual_prompt_price*1000).toFixed(3) : '自动'}</td>
          <td><span class="dot ${m.is_enabled ? 'ok' : 'error'}"></span>${m.is_enabled ? '启用' : '禁用'}</td>
          <td class="actions">
            <button class="btn-text" onclick="window._adminEditModel(${m.id})">编辑</button>
            <button class="btn-text danger" onclick="window._adminDelModel(${m.id})">删除</button>
          </td>
        </tr>`).join('');
    } catch (e) { console.error(e); }
  }

  window._adminEditModel = (id) => openModelForm(id);
  window._adminDelModel = async (id) => {
    if (!confirm('确定删除此模型配置？')) return;
    try { await APILLM.adminDeleteModel(id); loadAdminModels(); } catch(e) { alert(e.message); }
  };

  function openModelForm(id) {
    const title = id ? '编辑模型配置' : '新增模型配置';
    openModal(title, `
      <div class="form-group"><label>模型ID</label><input id="mf-id" class="input" placeholder="gpt-4o"></div>
      <div class="form-group"><label>展示名</label><input id="mf-name" class="input"></div>
      <div class="form-group"><label>分组</label><input id="mf-group" class="input" placeholder="GPT Series"></div>
      <div class="form-group"><label>手动价格 (prompt/Kt)</label><input id="mf-pprice" class="input" type="number" step="0.00001" placeholder="自动"></div>
      <div class="form-group"><label>手动价格 (completion/Kt)</label><input id="mf-cprice" class="input" type="number" step="0.00001" placeholder="自动"></div>
      <button class="btn primary" id="mf-submit" style="width:100%">保存</button>
    `, async () => {
      const data = {
        model_id: $('#mf-id').value, display_name: $('#mf-name').value,
        group_name: $('#mf-group').value,
        manual_prompt_price: parseFloat($('#mf-pprice').value) || null,
        manual_completion_price: parseFloat($('#mf-cprice').value) || null,
      };
      if (id) await APILLM.adminUpdateModel(id, data);
      else await APILLM.adminCreateModel(data);
      loadAdminModels();
    });
  }

  // ---------- 用户管理 ----------
  async function loadAdminUsers() {
    try {
      const data = await APILLM.adminListUsers();
      const tbody = $('#table-users tbody');
      tbody.innerHTML = data.map(u => `
        <tr>
          <td>${u.id}</td>
          <td>${esc(u.username)}</td>
          <td>${u.role === 'admin' ? '👑 管理员' : '👤 用户'}</td>
          <td>${u.balance}</td>
          <td><span class="dot ${u.is_active ? 'ok' : 'error'}"></span>${u.is_active ? '激活' : '禁用'}</td>
          <td class="actions">
            <button class="btn-text" onclick="window._adminEditUser(${u.id})">编辑</button>
            ${u.role !== 'admin' ? `<button class="btn-text danger" onclick="window._adminDelUser(${u.id})">删除</button>` : ''}
          </td>
        </tr>`).join('');
    } catch (e) { console.error(e); }
  }

  window._adminEditUser = (id) => openUserForm(id);
  window._adminDelUser = async (id) => {
    if (!confirm('确定删除此用户？')) return;
    try { await APILLM.adminDeleteUser(id); loadAdminUsers(); } catch(e) { alert(e.message); }
  };

  function openUserForm(id) {
    openModal(id ? '编辑用户' : '新建用户', `
      <div class="form-group"><label>用户名</label><input id="usr-name" class="input"></div>
      <div class="form-group"><label>密码</label><input id="usr-pass" class="input" type="password" placeholder="留空不修改"></div>
      <div class="form-group"><label>角色</label><select id="usr-role" class="input"><option value="user">用户</option><option value="admin">管理员</option></select></div>
      <div class="form-group"><label>余额</label><input id="usr-balance" class="input" type="number" step="0.01" value="0"></div>
      <button class="btn primary" id="usr-submit" style="width:100%">保存</button>
    `, async () => {
      const data = { username: $('#usr-name').value, role: $('#usr-role').value, balance: parseFloat($('#usr-balance').value) || 0 };
      const pass = $('#usr-pass').value;
      if (pass) data.password = pass;
      if (id) await APILLM.adminUpdateUser(id, data);
      else await APILLM.adminCreateUser(data);
      loadAdminUsers();
    });
  }

  // ---------- 数据看板 ----------
  async function loadAdminStats(by = 'models') {
    const table = $('#table-stats');
    table.querySelector('thead tr').innerHTML = `<th>${by === 'models' ? '模型' : '上游'}</th><th>调用次数</th><th>Token输入</th><th>Token输出</th><th>费用</th>`;
    table.querySelector('tbody').innerHTML = '<tr><td colspan="5" class="message">统计 API 即将上线</td></tr>';
    // TODO: connect to /api/admin/stats/models or /api/admin/stats/upstreams
  }

  // ============================================================
  // 用户后台
  // ============================================================
  function initUserTabs() {
    $$('#user-tabs .tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        $$('#user-tabs .tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        $$('#view-user .tab-panel').forEach(p => p.classList.remove('active'));
        $(`#user-tab-${tabName}`).classList.add('active');
        if (tabName === 'keys') loadUserKeys();
        if (tabName === 'logs') loadUserLogs();
        if (tabName === 'stats') loadUserStats();
      });
    });
    $('#btn-key-create').addEventListener('click', createApiKey);
  }

  async function loadUserKeys() {
    const tbody = $('#table-keys tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="message">API Key 管理即将上线</td></tr>';
    // TODO: GET /api/user/keys
  }

  async function createApiKey() {
    alert('API Key 创建功能即将上线');
    // TODO: POST /api/user/keys
  }

  async function loadUserLogs() {
    const tbody = $('#table-logs tbody');
    tbody.innerHTML = '<tr><td colspan="6" class="message">调用日志即将上线</td></tr>';
    // TODO: GET /api/user/logs
  }

  async function loadUserStats() {
    $('#user-stat-cards').innerHTML = '<div class="message">数据看板即将上线</div>';
    // TODO: GET /api/user/stats
  }

  // ============================================================
  // 弹窗
  // ============================================================
  function openModal(title, bodyHTML, onSubmit) {
    $('#modal-title').textContent = title;
    $('#modal-body').innerHTML = bodyHTML;
    $('#modal-overlay').style.display = 'flex';

    const submitBtn = $('#modal-body').querySelector('button[id$="-submit"]');
    if (submitBtn && onSubmit) {
      submitBtn.addEventListener('click', async () => {
        try { await onSubmit(); closeModal(); } catch(e) { alert(e.message); }
      });
    }

    $('#modal-close').onclick = closeModal;
    $('#modal-overlay').onclick = (e) => { if (e.target === $('#modal-overlay')) closeModal(); };
  }

  function closeModal() {
    $('#modal-overlay').style.display = 'none';
  }

  function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ============================================================
  // 启动
  // ============================================================
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
