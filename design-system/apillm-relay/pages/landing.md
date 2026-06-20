# APILLM Relay — 前端展示站设计方案

> **参考来源**: MiMo (mimo.xiaomi.com) + UI/UX Pro Max 设计系统
> **生成日期**: 2026-06-20
> **覆盖规则**: 本页覆盖 MASTER.md 中的 Vibrant & Block-based 风格，采用 **暗色极简主义 + 夸张排版** 路线

---

## 一、设计理念

### 核心关键词
**极简 / 暗色 / 夸张排版 / 流动文字 / 精密 / 专业**

### 设计哲学
APILLM 是一个「大模型的中转站」——它本身不产生内容，而是让内容流动得更聪明、更便宜。设计应当传递三个感受：

1. **精密可靠** — 像一个精密的瑞士钟表，安静但极其精确地工作
2. **透明简约** — 用户不需要看到复杂，只需要感受到简洁
3. **技术美感** — 用排版和动画本身来传递「这是工程师为工程师打造的工具」

MiMo 页面的核心设计语言是「用文字做背景」——大量重复的 "M I M O" 填满首屏，营造出沉浸式的技术氛围。这种手法来自 **夸张极简主义（Exaggerated Minimalism）**，我们将其嫁接到 APILLM 上。

---

## 二、色彩系统

### 主色调（暗色 OLED 优化）

| 角色 | 色值 | Tailwind | 用途 |
|------|------|----------|------|
| 背景色（深） | `#080808` | 自定义 | 主背景，接近纯黑但保留细微暖度 |
| 背景色（卡片） | `#111111` | 自定义 | 卡片、代码块、次要区域 |
| 边框色 | `#1A1A1A` | 自定义 | 极细微分割线，几乎不可见 |
| 主文字 | `#FAFAFA` | `text-gray-50` | 标题、正文 |
| 次文字 | `#888888` | `text-gray-500` | 辅助说明、日期、标签 |
| 强调色 | `#3B82F6` | `text-blue-500` | 链接、CTA 按钮、高亮 |
| 强调色（辅）| `#22C55E` | `text-green-500` | 状态指示（健康/在线）、价格优势 |
| 代码背景 | `#0D1117` | GitHub Dark | 代码块 |

### 配色原则
- **只有 2 个强调色**：蓝色（主）+ 绿色（功能）
- **没有渐变、没有阴影扩散**：极简到极致
- **边框只用 1px 极细线**：`border-white/5` 或 `border-white/10`
- **文字层级只靠粗细和大小区分**，不用颜色

### 与 MiMo 的差异
MiMo 使用纯黑白（几乎看不到强调色），我们稍微强化蓝色和绿色的功能性，因为 API 产品需要清晰的状态指示。

---

## 三、字体排版

### 字体选择

| 层级 | 字体 | 权重 | 用途 |
|------|------|------|------|
| Display（超大标题） | **Outfit** | 700-800 | Hero 主标题、章节大标题 |
| Heading | **Outfit** | 500-600 | 二级标题、卡片标题 |
| Body | **Inter** | 400-500 | 正文、描述 |
| Code | **JetBrains Mono** | 400 | 代码块、API 路径、密钥 |

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
```

### 排版层级

```
Hero 标题:     clamp(3rem, 8vw, 7rem)    / Outfit 800 / tracking-tighter / leading-none
章节标题:      clamp(2rem, 4vw, 3.5rem)  / Outfit 600 / tracking-tight
卡片标题:      1.25rem / 20px               / Outfit 500
正文:          1rem / 16px                  / Inter 400 / leading-relaxed
代码:          0.875rem / 14px              / JetBrains Mono 400
辅助文字:      0.75rem / 12px              / Inter 400 / text-gray-500
```

### MiMo 风格核心
MiMo 的 Hero 区域使用了**极大字号 + 极小字间距（tracking-tighter）+ 极小行高（leading-none）**，让文字几乎「挤压」在一起，产生视觉冲击力。同时，背景重复文字的透明度和字间距被拉得很开（tracking-widest），形成「密/疏」的对比。

---

## 四、页面结构

### 单页滚动设计（Single Page）

```
┌──────────────────────────────────────────────┐
│  NAV  (fixed, 透明→实色 on scroll)            │
│  [APILLM]                    [文档] [GitHub]  │
├──────────────────────────────────────────────┤
│                                               │
│  HERO  (100vh)                                │
│  ┌─ 背景: 重复 "A P I L L M" 文字矩阵 ────┐  │
│  │  A P I L L M  A P I L L M  A P I L L M │  │
│  │  R E L A Y    R E L A Y    R E L A Y   │  │
│  │  P R O X Y    P R O X Y    P R O X Y   │  │
│  │  (不同字号/透明度/速度 的 parallax)     │  │
│  └────────────────────────────────────────┘  │
│                                               │
│  APILLM                                       │
│  大模型智能中转                                │
│  一行代码，接入所有模型，永远走最便宜的路线       │
│  [快速开始]  [查看文档]                        │
│                                               │
├──────────────────────────────────────────────┤
│                                               │
│  WHAT (简介)                                  │
│  APILLM 是什么？                              │
│  3 句话说明 + 架构简图                         │
│                                               │
├──────────────────────────────────────────────┤
│                                               │
│  FEATURES (Bento Grid)                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │ 💰 智能  │  │ 🩺 健康  │  │ 🔄 协议  │      │
│  │   路由   │  │   监控   │  │   转换   │      │
│  └─────────┘  └─────────┘  └─────────┘      │
│  ┌──────────────────┐  ┌─────────┐           │
│  │ 📊 实时价格监控   │  │ 🔑 API  │           │
│  │                  │  │   密钥   │           │
│  └──────────────────┘  └─────────┘           │
│                                               │
├──────────────────────────────────────────────┤
│                                               │
│  QUICK START (代码块)                          │
│  一行命令开始使用                              │
│  ┌───────────────────────────────────────┐   │
│  │ $ curl https://api.apillm.com/v1/     │   │
│  │   chat/completions \                  │   │
│  │   -H "Authorization: Bearer sk-..." \ │   │
│  │   -d '{"model":"gpt-4o","messages":   │   │
│  │        [{"role":"user","content":     │   │
│  │          "Hello!"}]}'                 │   │
│  └───────────────────────────────────────┘   │
│                                               │
├──────────────────────────────────────────────┤
│                                               │
│  STATUS (实时状态 - 可选)                      │
│  上游模型可用性 / 当前价格对比                  │
│                                               │
├──────────────────────────────────────────────┤
│                                               │
│  FOOTER                                       │
│  © 2026 APILLM  |  GitHub  |  文档  |  状态   │
│                                               │
└──────────────────────────────────────────────┘
```

---

## 五、核心动画设计

### 1. Hero 重复文字矩阵（MiMo 风格核心动画）

**实现原理**: 多层 Canvas 或 DOM 文字层，以不同速度滚动/平移，产生深度视差效果。

```
Layer 1 (最远): "A P I L L M" × 20 列, 字号 sm, opacity 0.08, speed 0.2x
Layer 2:        "R E L A Y"   × 15 列, 字号 base, opacity 0.12, speed 0.5x
Layer 3:        "P R O X Y"   × 10 列, 字号 lg, opacity 0.18, speed 0.8x
Layer 4 (最近): "A P I L L M" × 5 列,  字号 xl, opacity 0.25, speed 1.2x
```

**技术方案**:
- 使用 CSS `@keyframes` + `transform: translateX()` 循环滚动
- 每层独立 `animation-duration`，产生交错速度
- 使用 `will-change: transform` 优化 GPU 合成
- 随页面滚动，整个矩阵做 `translateY` 上移 + `opacity` 渐隐

**关键 CSS**:
```css
.hero-text-matrix {
  position: absolute;
  inset: 0;
  overflow: hidden;
  mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
}

.matrix-row {
  display: flex;
  gap: 2rem;
  white-space: nowrap;
  animation: scrollLeft var(--speed) linear infinite;
}

@keyframes scrollLeft {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
```

### 2. 滚动渐现动画（Scroll Reveal）

- 每个 section 进入视口时触发 `opacity: 0→1` + `translateY: 24px→0`
- 使用 Intersection Observer API
- 动画时长 600ms，ease-out
- 各卡片 stagger 延迟 100ms

### 3. 代码块打字效果（可选）

Quick Start 区域的代码块可以做逐行打印效果，但当用户已滚动到该区域时直接显示全部（避免等待）。

### 4. Navbar 滚动变化

- 初始: `bg-transparent`, 文字白色
- 滚动超过 Hero 后: `bg-[#080808]/90 backdrop-blur-xl`, 底部 `border-white/5`

### 5. 数字跳动（Status 区域）

- 价格数据做 `countUp` 动画
- 健康状态指示灯做 `pulse` 动画（绿色呼吸灯效果）

### 动画原则
- 所有动画 `duration` 在 200-800ms 范围
- 尊重 `prefers-reduced-motion`
- 不滚动劫持（no scroll-jacking）
- 无限循环动画仅用于 Hero 背景和状态指示灯

---

## 六、组件规范

### Logo / 品牌标识
- 纯文字标: **APILLM**，使用 Outfit 800，tracking-tighter
- 或者: **APILLM** 其中 "API" 用 regular weight，"LLM" 用 bold weight
- 不加图标，极简到只有文字

### 导航栏
- 高度: 56px (h-14)
- 固定顶部，z-50
- 左侧: Logo 文字
- 右侧: 文档 / GitHub (图标) / 语言切换
- 滚动后加毛玻璃背景

### 按钮

```css
/* 主要按钮 (Hero CTA) */
.btn-primary {
  background: #3B82F6;           /* bg-blue-500 */
  color: white;
  padding: 14px 32px;
  border-radius: 8px;
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.01em;
  transition: all 200ms ease;
}
.btn-primary:hover {
  background: #2563EB;           /* bg-blue-600 */
  transform: translateY(-1px);
}

/* 次要按钮 */
.btn-secondary {
  background: transparent;
  color: #FAFAFA;
  border: 1px solid rgba(255,255,255,0.15);
  padding: 14px 32px;
  border-radius: 8px;
  font-family: 'Outfit', sans-serif;
  font-weight: 500;
  font-size: 16px;
  transition: all 200ms ease;
}
.btn-secondary:hover {
  border-color: rgba(255,255,255,0.4);
  background: rgba(255,255,255,0.05);
}
```

### 卡片（Bento Grid 特性卡片）

```css
.feature-card {
  background: #111111;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 32px;
  transition: all 300ms ease;
  cursor: pointer;
}
.feature-card:hover {
  background: #181818;
  border-color: rgba(255,255,255,0.12);
  transform: translateY(-4px);
}
```

### 代码块

```css
.code-block {
  background: #0D1117;           /* GitHub dark */
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 24px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  line-height: 1.7;
  overflow-x: auto;
}
```

### 分割线
- 不使用可见分割线
- 用 120px 以上的垂直间距来区分 section
- 在需要分割的地方使用 `border-t border-white/5`

---

## 七、技术方案

### 推荐技术栈: Next.js 14 + Tailwind CSS v4

| 层 | 选择 | 理由 |
|----|------|------|
| 框架 | **Next.js 14** (App Router) | SSR/SSG，SEO 友好，Vercel 一键部署 |
| 样式 | **Tailwind CSS v4** | 原子化 CSS，暗色模式内置，与设计系统契合 |
| 动画 | **Framer Motion** | React 动画事实标准，支持 scroll-triggered、layout、gesture |
| 图标 | **Lucide React** | 高质量 SVG 图标，Tree-shaking，MIT 协议 |
| 代码高亮 | **Shiki** | 构建时语法高亮，零运行时 JS |
| 字体 | **next/font** | 自动子集化 + 无闪烁加载 |
| 部署 | **Vercel** 或 **Cloudflare Pages** | 全球 CDN，免费额度足够 |

### 备选方案: 纯 HTML + Tailwind（更简单）

如果不需要 React，可以用 **Astro** 或纯 HTML + Tailwind CDN，更轻量：

```html
<!-- 纯静态方案 -->
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        fontFamily: {
          display: ['Outfit', 'sans-serif'],
          body: ['Inter', 'sans-serif'],
          mono: ['JetBrains Mono', 'monospace'],
        },
        colors: {
          bg: '#080808',
          card: '#111111',
          border: '#1A1A1A',
        }
      }
    }
  }
</script>
```

### 与既有 API 对接

前端展示站是**纯静态页面**，可以通过以下方式对接：

1. **API 文档链接**: 直接链接到 FastAPI 自带的 `/docs`（Swagger UI）
2. **状态展示**: 如果 `/health` 端点对外暴露，前端可以用 fetch 拉取实时状态
3. **Quick Start 代码**: 静态展示，用户复制后在自己的环境中使用
4. **无需后端渲染**: 前端完全独立部署，API 服务独立运行

---

## 八、实现路线

### Phase 1: 基础框架 + Hero（1-2天）
- [ ] 初始化 Next.js 项目 + Tailwind v4
- [ ] 配置字体 (Outfit + Inter + JetBrains Mono)
- [ ] 实现 Hero 区域 + 重复文字矩阵动画
- [ ] 实现 Navbar（含滚动效果）

### Phase 2: 内容区域（1-2天）
- [ ] WHAT 简介区域
- [ ] FEATURES Bento Grid（5 个特性卡片）
- [ ] QUICK START 代码展示
- [ ] FOOTER

### Phase 3: 动画打磨（1天）
- [ ] Scroll Reveal（Intersection Observer）
- [ ] 卡片 hover 效果
- [ ] 数字跳动效果
- [ ] prefers-reduced-motion 适配

### Phase 4: 响应式 + 部署（1天）
- [ ] 移动端适配（375px / 768px / 1024px / 1440px）
- [ ] Vercel 部署
- [ ] 性能优化（Lighthouse > 90）

---

## 九、Hero 动画详细规格

### 文字矩阵参数

```
总区域: 100vh × 100vw
行数: 8-10 行（根据视口高度自动调整）
每行文字: "A P I L L M" 或 "R E L A Y" 或 "P R O X Y" 交替
字号: 14px / 20px / 28px / 40px（4层）
透明度: 0.06 / 0.10 / 0.16 / 0.22（4层）
滚动速度: 120s / 80s / 50s / 30s（4层，线性无限循环）
字间距: 2rem / 3rem / 4rem / 6rem
```

### 标题叠加层

```
z-10 覆盖在文字矩阵之上:
"APILLM"       → Outfit 800, clamp(4rem, 10vw, 8rem), tracking-tighter
"大模型智能中转" → Outfit 400, clamp(1.25rem, 2.5vw, 2rem), text-gray-400
"一行代码，接入所有模型，永远走最便宜的路线"
               → Inter 400, 1.125rem, text-gray-500
[快速开始] [查看文档] → 两个按钮并排
```

### 滚动行为

当用户向下滚动时：
- Hero 文字矩阵整体 `translateY(-30vh)` + `opacity → 0`
- 标题在 Hero 区域内固定（sticky），直到完全离开视口
- Navbar 从透明变为毛玻璃

---

## 十、预交付检查清单

- [ ] 无 Emoji 作图标（使用 Lucide SVG）
- [ ] 所有可点击元素有 `cursor-pointer`
- [ ] hover 状态使用 `transition-colors duration-200`
- [ ] 暗色模式下文字对比度 ≥ 4.5:1（已满足：`#FAFAFA` on `#080808` = 18:1）
- [ ] 键盘焦点可见（focus-visible ring）
- [ ] 尊重 `prefers-reduced-motion`
- [ ] 375px / 768px / 1024px / 1440px 断点均有适配
- [ ] 无水平滚动条
- [ ] 图片有 alt 文本
- [ ] 页面加载 < 2s (Lighthouse)
