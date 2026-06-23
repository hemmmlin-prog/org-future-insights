# DESIGN-NOTES · org-future-insights

> **目的**：记录 SKILL 设计的关键决策与权衡，支撑后续迭代不偏航
> **创建**：2026-06-14（v0.1）
> **最近更新**：2026-06-14（v0.3.0 接入百炼后翻案 + 三层架构）

---

## 0. v0.3.0 核心翻案（最重要）

v0.1 DESIGN-NOTES 第 3 节的论断：

> "在不脱离 Qoder 体系的前提下，全自动每日报告做不到。launchd 解决抓取，分析仍需手动触发——但这只多 5 秒。"

**这个判断在 v0.3.0 被翻案**。原因：**Qoder Agent 不是唯一能做分析的 LLM**——把分析层从 Qoder 内迁移到本地脚本调阿里云百炼 qwen-max API，就能在 launchd 体系内完成"抓取 + 分析 + 分流"全闭环。

**新论断**：站点已真正"每天自动更新"，SKILL 的价值从"生成"转为"审阅 + 补刀 + 兜底"。详见第 7 节新三层架构。

---

## 1. 为什么是 4 模式（v0.1 是 3 模式）

| 模式 | v0.1 | v0.3.0 | 理由 |
|---|---|---|---|
| A. 实时对话查询 | ✅ | ✅ 加强 | 用户高频；现在还能拿 8 板块 auto-md 作为弹药 |
| B. 每日深度报告 | ✅ 生成式 | ✅ **改为审阅/补刀** | 百炼已自动生成 auto 版；SKILL 做 pm 精读版（含强反方/中国映射）|
| C. 分享导出 | ✅（预留）| ✅（预留）| 用户明确需求 ③，但不阻塞主流程 |
| **D. 手动 pipeline 兜底** | ❌ | **✅ 新增** | launchd 偶发失败 / 临时想更新快照 / 测 prompt 都需要 |
| ~~周报聚合~~ | ❌ | ❌ | v0.4 再考虑；可以让百炼跑 weekly aggregate |

---

## 2. 为什么深度报告（模式 B）仍坚持 3000 字

- 百炼 auto 版只有 ~2000 字，3 信号通读级，没足够篇幅做"反方深度 × 顶刊分级 × 中国映射 × mermaid × 矩阵"
- 模式 B 精读版（pm 版）补的就是这些 — **价值密度 vs auto 版的 2-3 倍**
- 文件命名 `YYYY-MM-DD-pm.md`，与 `YYYY-MM-DD-auto.md` 并存不替换，HR 同事可自选深浅

---

## 3. 为什么 v0.3.0 选阿里云百炼 qwen-max

| 维度 | qwen-max | GPT-4 / Claude | 自托管 LLM |
|---|---|---|---|
| 中文质量 | ✅ 顶级 | ⚠️ 良好但偶尔翻译腔 | ❌ 弱 |
| API 价格 | ✅ ~¥3/月 | ❌ ~$20/月 | ✅ 0 但硬件成本高 |
| 中国境内可用性 | ✅ 直连 | ❌ 需代理 | ✅ |
| OpenAI 兼容协议 | ✅ | ✅ | ⚠️ |
| HR / 组织管理语料覆盖 | ✅（百炼训练含大量中文管理类）| ⚠️ 偏英文 | ❌ |

**决策权重**：中文质量 > 价格 > 可用性 > 兼容性。qwen-max 全部领先。

---

## 4. 为什么调度仍用 launchd 本地（不上云）

| 评估维度 | launchd + 百炼（v0.3.0）| GitHub Actions + 百炼 |
|---|---|---|
| 抓取自动化 | ✅ 06:00 | ✅ |
| 分析自动化 | ✅ 06:30（百炼）| ✅ |
| 数据隐私 | ✅ raw 留本地，仅文本走 API | ⚠️ raw 上 GitHub |
| 用户偏好"不依赖跨会话后台运行" | ✅ launchd 本质上是本机的 | ❌ |
| 实施复杂度 | ⭐⭐ | ⭐⭐⭐⭐ |
| Mac 关机时 | ⚠️ 跳过（RunAtLoad 补跑）| ✅ |

> 唯一短板（Mac 关机当天跳过）由模式 D 手动兜底解决。

---

## 5. 为什么继承 hr-role-insight v0.4 的 9 类提示词模式

- 已在 5 个主题（HR 角色 / VC 视角 / 学术分级 / 反方专题 / 绩效与激励）上验证稳定
- 模式 A 实时查询直接复用；**模式 B 精读版也按这套结构**
- 词典 / 信源池 / 自检清单都直接复用 `_SKILL草稿_hr-role-insight/` 资产

---

## 6. 为什么信源池放在 reference/，而不是 SKILL.md 内

- SKILL.md 必须 < 500 行（Qoder 规范）
- 信源池有 50+ 条带 RSS / 中英对照，200+ 行
- 渐进式披露：Agent 在用到时再读，节省每次调用的 token 成本

---

## 7. v0.3.0 三层架构图（取代 v0.1 双层）

```
┌─────────────────────────────────────────────────────────────────┐
│ 第 1 层：抓取（launchd 06:00，无人值守）                          │
│   fetch_daily.py 抓 19 源 → ~/org-future-insights/daily-raw/    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第 2 层：百炼自动分析（launchd 06:30，无人值守，v0.3.0 新增）       │
│   bailian/pipeline.py:                                          │
│     ├─ A: qwen-max → daily-reports/YYYY-MM-DD-auto.md           │
│     └─ B: qwen-max → companies/auto-*.md, research/auto-*.md,   │
│                       cases/, readings/, dictionary/,           │
│                       dashboard/, events/, daily_only           │
│   成本 ~¥0.10/天，耗时 ~2.5 分钟                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第 3 层：用户增量（Qoder SKILL，按需触发）                         │
│   /org-future-insights "..."   → 模式 A 实时查询                 │
│   /org-future-insights --review → 模式 B 审阅 / 补刀 → pm 版     │
│   /org-future-insights --refresh → 模式 D 手动 pipeline 兜底     │
│   /org-future-insights --share   → 模式 C 分享                  │
└─────────────────────────────────────────────────────────────────┘
```

**与 v0.1 关键区别**：第 2 层从"Qoder 内手动触发"迁出，变成 launchd 全自动。SKILL 不再是"日报生成器"，而是"日报精读 + 兜底 + 实时问答"工具。

---

## 8. 风险与缓解（v0.3.0 更新）

| 风险 | 缓解 |
|---|---|
| Mac 关机/睡眠 → launchd 06:00/06:30 都跳过 | 模式 D 手动跑 `python3 -m bailian.pipeline` |
| 百炼 quota 用尽 / 网络故障 | client.py 已 3 次重试；失败时退出码 1，pipeline.log 留痕；可降级 `--model qwen-plus` 省 75% 成本继续跑 |
| 百炼返回 `module_tags` 字符串而非数组 | classify_to_modules.py 已加 isinstance 兜底 + prompt 第 6 条强制数组要求（v0.3.0 实测中发现并修复）|
| 信源 RSS 失效 / 403 | fetch_daily.py 单源失败不中断，只记 log |
| daily-raw 文件累积膨胀 | 保留最近 30 天，手动归档老数据到 archive/ |
| API Key 泄露 | 存在 `~/.config/org-future-insights/.env` 600 权限，工作区只有 `.env.example` 不含真 key |

---

## 9. 未实现 / v0.4 路线图

- [x] ~~全自动每日报告~~ **v0.3.0 已实现**
- [ ] **模式 C 完整实现**：vercel-deploy / 微信公众号格式 / PDF 导出
- [ ] **周报自动化**：周日凌晨另跑一个 weekly-aggregate（让百炼基于 7 天 auto 报告做 meta 分析）
- [ ] **主题订阅**：用户可设置"我关注绩效改革 + Skills-based pay"，daily 报告优先这些
- [ ] **多语言**：模式 B 输出英文摘要供国际同事
- [ ] **告警**：某议题"信号强度"突变（如 NBER 发新工作论文），主动 push macOS 通知
- [ ] **dictionary 自动收录**：当百炼分流出 `dictionary` 标签时，自动 propose 新术语并 append 到 `dictionary/glossary.md`
- [ ] **dashboard 数据点提取**：百炼分流到 `dashboard` 时同时输出结构化 JSON（{metric, value, source, date}），自动入数据库

---

## 10. 与现有资产的关系

```
组织演变/
├── 知识包 6 件套                       ← 母体内容（人写的）
├── _SKILL草稿_hr-role-insight/         ← 提示词模式 + 词典 + 模板（被本 SKILL + bailian/prompts 共同复用）
├── bailian/                            ← v0.3.0 自动层（脚本）
└── .qoder/skills/org-future-insights/  ← 本 SKILL（Agent 增量层）
       │
       └── 产出 daily-reports/*-pm.md   ← 精读版进 Docsify
                companies/ etc          ← 8 板块手工内容（与百炼的 auto-*.md 并存）
```

**关键复用链**：
- 9 类提示词模式 → SKILL 模式 A/B 用 + bailian/prompts/daily_report.txt 用
- HR 视角元逻辑（5 类基线 / 反方 / 中国映射）→ bailian/prompts/role_system.txt 把它固化为 system prompt
- 概念词典 → SKILL 优先查 + 模式 B 补刀时给百炼输出加术语锚点

---

## 11. 决策溯源

| 决策 | 时间 | 触发 |
|---|---|---|
| 命名 org-future-insights | 2026-06-14 上午 | 用户 Q1 选 B |
| 调度 launchd 本地 | 2026-06-14 上午 | 用户回应"采取 A 方案" |
| 深度 3000 字 | 2026-06-14 上午 | 用户 Q3 选 C |
| 路径 create-skill + 决策日志并行 | 2026-06-14 上午 | 用户接受推荐 C |
| HR 内容门户 8 板块 | 2026-06-14 下午 | 用户主动需求"做成可读站点" |
| **接入百炼 qwen-max** | **2026-06-14 晚** | **用户"接入阿里云百炼 API，尝试优化" → 选 A+B 组合 + qwen-max** |
| **API Key 走 ~/.config/.env** | **2026-06-14 晚** | **安全决策：不进 conversation history、不进 git** |

---

## 12. 版本

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-06-14 上午 | 初版决策日志，对应 SKILL v0.1 |
| v0.2 | 2026-06-14 下午 | HR 内容门户 8 板块上线，SKILL 模式 A 弹药库扩展 |
| **v0.3.0** | **2026-06-14 晚** | **接入百炼翻案：第 0/3/7/8/9/11 节大改；4 模式架构；三层架构图；运营成本表上线** |
