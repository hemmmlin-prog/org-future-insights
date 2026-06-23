---
name: org-future-insights
description: |
  HR-perspective future-of-work intelligence SKILL for 速卖通 HRBP Leader（供给+供应链团队）。
  v0.5.0 新增 --action 模式：基于当日信号自动生成 HRBP 专属行动计划（含 Excel 导出）。
  完整 6 模式：(A) 实时深挖查询 (B) PM 精读补刀 (C) 分享导出 (D) 一键日报 (E) 质量审计 (F) 行动计划。
  触发条件：用户问 future of work / agentic enterprise / HR 变革 / 组织设计 / AI 对岗位的影响 / 行动计划 / 今天有什么启发，
  或显式 /org-future-insights 加 --daily / --review / --share / --action / --audit / 主题查询。
---

# org-future-insights · v0.5.0

> 速卖通 HRBP Leader 专属 · HR 视角未来组织趋势洞察 SKILL
> 一键全流程：抓取 → 日报 → 分流 → 可视化 → 审计 → **行动计划（NEW）**

---

## 一、当前世界（v0.4.0 请先读这块）

**站点已经全自动**——你每天打开 Qoder 之前，下面这些事都已经发生：

```
06:00  launchd 跑 scripts/fetch_daily.py
       → 抓 19 源 → daily-raw/YYYY-MM-DD.json
06:30  launchd 跑 python3 -m bailian.pipeline
       → 阶段 A (qwen-max ~70s): daily-reports/YYYY-MM-DD-auto.md
       → 阶段 B (qwen-max ~76s): 8 板块各写 auto-YYYY-MM-DD.md 聚合
       → 阶段 C (~0.3s): daily-reports/YYYY-MM-DD-visual.md 可视化页
       → 阶段 D (~0.1s): _sidebar.md 自动挂载
       → 阶段 E (~0.2s): 6 项质量审计 → _logs/YYYY-MM-DD-audit.json
06:33  全部产物就绪，HR 同事打开站点就能看
```

*你（用户 = 速卖通 HRBP Leader，支持供给+供应链团队）打开 Qoder 之后的真实工作流**：

| 高频场景 | 用什么 | 典型说法 |
|---|---|---|
| 想知道今天发生什么 | **不调 SKILL**，直接打开 `daily-reports/YYYY-MM-DD-visual.md` | （只读，可视化版更佳）|
| 看了 auto 版想就某条信号继续深挖 | **模式 A** | "AI 对供应链岗位的影响" / "agentic enterprise 在中国落地" |
| auto 版某段写得不到位 / 反方不够硬 | **模式 B（增量编辑）** | "把今天 auto 版的信号 1 反方再加 NBER 实证" |
| 想基于今日信号生成本周行动计划 | **模式 F（行动计划）** | "给我出一个行动计划" / `/org-future-insights --action` |
| auto 版根本没生成（Mac 睡眠 / 抓取失败）| **模式 D（一键日报）** | "今天 auto 版没出来，跑一遍" 或 `/org-future-insights --daily` |
| 全量重新生成（已有版本不满意）| **模式 D + --force** | "把今天的 auto 版重生成，用 qwen-plus 省钱" |
| 想把某天报告分享给 CHRO / VP | **模式 C** | "把今天的报告打包给我" |

> **关键认知**：v0.5.0 的核心价值是"**一键全流程 + 可视化 + 自动审计 + 行动计划直出**"。从信号到落地行动只需两步。

---

## 二、六种调用模式

| 调用 | 模式 | 输出 |
|---|---|---|
| `/org-future-insights "主题"` | A. 实时对话查询 | 当场答复（500–1500 字，按需 mermaid）|
| `/org-future-insights --review` 或 `--patch "改进点"` | B. 审阅 / 补刀 auto 日报 | 新增 `YYYY-MM-DD-pm.md`（增量精读版）|
| `/org-future-insights --share <topic-or-date>` | C. 分享导出 | 单文 / ZIP / Docsify URL |
| `/org-future-insights --daily [--force] [--model qwen-plus]` | D. 一键日报（全流程） | fetch → 日报 → 分流 → 可视化 → 侧边栏 → 审计 |
| `/org-future-insights --audit [date]` | E. 单独质量审计 | 6 项自检报告 + audit.json |
| `/org-future-insights --action [date]` | **F. 行动计划（v0.5.0 新增）** | HRBP 行动计划 + Excel 导出 + Canvas 看板 |

---

## 模式 A：实时对话查询

### 触发
- 用户发问含"未来组织 / 智能体企业 / HR 变革 / agentic / orchestrator / mindset > skillset / underground AI use" 等关键词
- 或显式 `/org-future-insights "查询主题"`

### 执行步骤
1. **理解查询**：拆"主题 + 角度 + 时间窗"三要素
2. **先查工作区**（按优先级）：
   - a. 今天的 `daily-reports/YYYY-MM-DD-auto.md` + 8 板块 `auto-YYYY-MM-DD.md`（百炼已沉淀的素材）
   - b. `dictionary/glossary.md` 词典
   - c. 历史 `daily-reports/`、`research/`、`companies/` 既有沉淀
3. **若工作区未覆盖**：调 `WebSearch` + `WebFetch` 补 3–5 个权威源（必须命中 5 类多源最低基线中至少 3 类）
4. **按 9 类提示词模式输出**：见 [reference/prompt-patterns.md](reference/prompt-patterns.md)
5. **必出反方**：至少 1 条 HBR / NBER / Brookings 反方对冲
6. **诚实边界**：标注信息时效性快照 + 不确定的明确说"未确认"

### 输出模板
按 [templates/interactive-qa.md](templates/interactive-qa.md) 结构。

---

## 模式 B：审阅 / 补刀百炼自动日报

### 何时用
- auto 版反方不够硬 → 补 NBER / Brookings 实证
- auto 版中国语境太弱 → 补 36Kr / 北森 / 国资委映射
- auto 版漏了今日某条关键新闻 → 主动补
- 用户想出一版"HR 总监级精读版"（vs auto 版的"通读级"）

### 执行步骤
1. **读 auto 版**：`daily-reports/YYYY-MM-DD-auto.md`
2. **读 raw**：`~/org-future-insights/daily-raw/YYYY-MM-DD.json`（找 auto 版没用上的好素材）
3. **读 8 板块 auto 文件**（companies/research/cases/readings/dashboard/events 的 `auto-YYYY-MM-DD.md`），定位深挖钩子
4. **按用户给的改进点定向编辑**，或默认补 3 件事：
   - 反方对冲深度（至少 1 条 NBER + 1 条 Brookings / HBR）
   - 中国本土映射（至少 2 条）
   - 5 类多源覆盖度自检
5. **写出 pm 版**：`daily-reports/YYYY-MM-DD-pm.md`（与 auto 版并存不替换）
6. 更新 `_sidebar.md` 把 pm 版挂入「📅 每日趋势 / YYYY-MM-DD」分组

### 输出模板
按 [templates/daily-report.md](templates/daily-report.md) 结构（3000 字 + mermaid + 共识矩阵 + 关键数据速查）。

---

## 模式 C：分享导出

### 触发
- `/org-future-insights --share <topic-or-date>`

### v0.1 当前能力
1. 把目标 MD 文件**复制内容到剪贴板**（`pbcopy < file.md`）
2. 把目标 MD + 引用图片**打包成 ZIP**
3. 若 Docsify 已在本地跑（`http://localhost:3000`），返回直链

### v0.4 预留（需用户单独触发开发）
- 集成 [vercel-deploy](../../vercel-deploy/SKILL.md) → 一键部署到公开 URL
- 微信公众号格式 / PDF 导出
- 分享卡片自动生成（[templates/shareable-card.md](templates/shareable-card.md) 已留模板）

---

## 模式 D：手动跑 fetch + 百炼 pipeline（兜底）

### 何时用
- 早上打开 Qoder 发现 `daily-reports/` 没有当天 `-auto.md` → launchd 漏跑（Mac 睡眠 / 网络故障 / 百炼 quota 限制）
- 临时想看“现在这一刻”的快照而不等到明早
- 测试 prompt / 模型切换效果（`--model qwen-plus` 省钱档 ≈ ¥0.02/天）

### 执行步骤（一条命令全搞定）
```bash
cd "/Users/emmah/Desktop/AI学习/Qoder文档/Emmafolder/组织演变"

# 1) 抓取（如 raw 已存在可跳过）
/usr/bin/python3 .qoder/skills/org-future-insights/scripts/fetch_daily.py --priority 2

# 2) 全流程 A+B+C+D+E
python3 -m bailian.pipeline                         # 默认 qwen-max，含可视化+侧边栏+审计
python3 -m bailian.pipeline --model qwen-plus       # 省钱档
python3 -m bailian.pipeline --skip-classify         # 只跑日报+可视化+审计
python3 -m bailian.pipeline --skip-visual           # 跳过可视化
python3 -m bailian.pipeline --skip-audit            # 跳过审计
python3 -m bailian.pipeline 2026-06-13              # 重跑历史某日
```

### 全流程产物

| 阶段 | 产物 | 成本 |
|---|---|---|
| A 日报 | `daily-reports/YYYY-MM-DD-auto.md` | ~¥0.05 |
| B 分流 | 8 板块 `auto-YYYY-MM-DD.md` | ~¥0.05 |
| C 可视化 | `daily-reports/YYYY-MM-DD-visual.md` | ¥0 |
| D 侧边栏 | `_sidebar.md` 自动更新 | ¥0 |
| E 审计 | `daily-raw/_logs/YYYY-MM-DD-audit.json` | ¥0 |

### 完成后交互式选项

pipeline 跑完后，SKILL 自动提示 4 个下一步选项：

```
🎉 全流程完成！下一步可选：
  1) /org-future-insights --review  → 出 PM 精读版（严格溯源）
  2) /org-future-insights --action  → 生成本周 HRBP 行动计划 + Excel
  3) /org-future-insights --share   → 打包分享给 VP/CHRO
  4) 直接打开 http://localhost:3000 查看可视化版
```

在 Qoder 内使用时，SKILL 会自动调用 `AskUserQuestion` 让用户选择。

### 失败排查
| 现象 | 排查 |
|---|---|
| `❌ 未找到 ~/.config/org-future-insights/.env` | 该文件丢失/被改，重新写入 `DASHSCOPE_API_KEY=sk-xxx` |
| `chat 第 3/3 次失败` 后退出 | 看百炼 quota：https://dashscope.console.aliyun.com/ |
| 分流板块文件没生成 | 看 `daily-raw/_logs/bailian.pipeline.log` 最后一行 |
| `module_tags` 报字符串错 | 已在 v0.3.0 加 isinstance 兆底，理论上不会再触发 |
| 可视化页未生成 | 确认 auto.md 已存在，或手动 `python3 -m bailian.generate_visual` |
| 审计报 WARN | 正常现象，查看 `_logs/YYYY-MM-DD-audit.json` 了解哪项未通过 |

---

## 模式 E：单独质量审计

### 触发
- `/org-future-insights --audit` 或 `/org-future-insights --audit 2026-06-16`

### 6 项强制自检

| # | 检查项 | 通过条件 |
|---|---|---|
| 1 | 5 类多源覆盖 | 命中类别 >= 3 |
| 2 | 反方对冲完整 | 每条信号都有对冲 |
| 3 | HR 三大支柱覆盖 | 招聘/发展/回报 >= 2 维 |
| 4 | 金句来源可溯 | >= 3/5 条能在 raw 中找到 |
| 5 | 总字数范围 | 2500-3500 字 |
| 6 | 信号类目多样 | 3 条信号不全来自同一类 |

输出：终端彩色 PASS/WARN 报告 + `daily-raw/_logs/YYYY-MM-DD-audit.json`

审计未通过时的处理：
- **自动流程（launchd）**：仅记录日志，不阻塞
- **手动流程（Qoder 内）**：SKILL 会提示“审计发现 N 项未通过，是否要我补强？”

---

## 模式 F：行动计划生成（v0.5.0 新增）

### 触发
- `/org-future-insights --action` 或 `/org-future-insights --action 2026-06-19`
- 用户说"给我出一个行动计划" / "今天的信号对我有什么启发" / "本周我该做什么"

### 用户背景
- **角色**：速卖通 HRBP Leader
- **支持团队**：供给团队（商家运营 / 类目招商 / 选品策略）+ 供应链团队（物流规划 / 需求预测 / 仓储调度）
- **上级**：业务 VP / HRD
- **下级**：HRG 团队

### 执行步骤
1. **读 PM 版（优先）或 auto 版**：提取“本周 HR 行动速查”板块 + 3 条核心信号
2. **映射到用户场景**：将通用 HR 行动翻译为“速卖通供给+供应链”具体动作
3. **分层输出**：
   - 本周（自己做）→ 下周（决策）→ 本月（推动）→ 本季（布局）
   - 每项标明：时间节点 / 行动项 / 负责人 / 产出物 / 关联信号源
4. **双格式交付**：
   - a. **Canvas 看板**：在 Qoder 右侧面板实时查看
   - b. **Excel 文件**：含多 Sheet（行动计划 / 岗位分档模板 / HRG 摸底作业），自动打开 Finder

### 行动计划结构规范

| 分层 | 时间窗 | 负责人典型 | 产出物典型 |
|---|---|---|---|
| 🔴 本周必做 | 1-5 天 | 自己 | 业务 1v1 判断 / HRG 摸底数据 |
| 🟠 本月推动 | 2-4 周 | 自己 + HRG | one-pager / 共生 JD / Workshop |
| 🟡 本季布局 | Q 级 | 自己 + 业务 Leader | OKR 写入 / 轮岗试点 |

### 中国映射严格溯源规则（从 v0.5.0 起强制）

> “中国映射”板块只允许引用 raw JSON 中实际存在的文章，**禁止 LLM 泛化推断**。
> 如 raw 中无直接对应的中国案例，应标注“本日 raw 未覆盖中国直接案例，以下为延伸参考”并给出 WebSearch 补充来源。

### 输出模板
按 [templates/action-plan.md](templates/action-plan.md) 结构。

---

## 三、强制规范（自动审计 + 人工自检）

**自动审计**（阶段 E）已覆盖前 6 项，每次 pipeline 跑完自动执行。

人工写报告 / 写答复时额外自检：

- [ ] **5 类多源基线**：咨询 / 科技 / 学术 / 智库 / VC 至少命中 3 类
- [ ] **真顶刊分级**：A+（FT50/UTD24 主刊）/ B（专业 SSCI）/ C（工作论文）要标清
- [ ] **HR 三大支柱**：招聘 / 发展 / 回报 任一议题不要漏
- [ ] **反方对冲**：含至少 1 条 HBR / NBER / Brookings 反方
- [ ] **VC 实证对冲**：引用 a16z / YC / Sequoia 必配 NBER 或 Brookings
- [ ] **快照时效**：每份报告标"截至 YYYY-MM-DD HH:MM 抓取"

完整 9 类提示词模式见 [reference/prompt-patterns.md](reference/prompt-patterns.md)。

---

## 四、工具白名单

| 工具 | 用于 |
|---|---|
| `Read` | 读 auto 日报 / raw JSON / 8 板块 auto-md / 知识包 MD |
| `Grep` / `Glob` | 在工作区检索关键词与历史素材 |
| `WebSearch` | 模式 A 实时查权威源最新发布 |
| `WebFetch` | 抓 RSS / 文章页 |
| `Write` | 模式 B 生成 `YYYY-MM-DD-pm.md` / 模式 C 写分享文件 |
| `SearchReplace` | 增量更新 _sidebar.md / README.md |
| `Bash` | 模式 D 调 pipeline；模式 F 生成 Excel（openpyxl）+ 打开文件；模式 C 打包/pbcopy |
| `Skill(canvas)` | 模式 F 生成 Canvas 看板（可视化行动计划）|

---

## 五、文件结构

```
组织演变/
├── .qoder/skills/org-future-insights/      ← 本 SKILL（你在这）
│   ├── SKILL.md                            ← 当前文件
│   ├── DESIGN-NOTES.md                     ← 决策日志（v0.3.0 三层架构）
│   ├── reference/
│   │   ├── source-pool.md                  ← 50+ 信源池
│   │   └── prompt-patterns.md              ← 9 类提示词模式
│   ├── templates/
│   │   ├── interactive-qa.md               ← 模式 A 输出模板
│   │   ├── daily-report.md                 ← 模式 B 3000 字精读版模板
│   │   └── shareable-card.md               ← 模式 C 分享卡片
│   └── scripts/                            ← 历史抓取脚本（v0.1）
│
├── bailian/                                ← v0.4.0 百炼自动化（与 SKILL 配对）
│   ├── client.py                           ← OpenAI 兼容客户端
│   ├── generate_daily.py                   ← A：自动日报
│   ├── classify_to_modules.py              ← B：8 板块分流
│   ├── generate_visual.py                  ← C：可视化页面生成（零 API 成本）
│   ├── update_sidebar.py                   ← D：侧边栏自动更新
│   ├── quality_audit.py                    ← E：6 项质量审计
│   ├── pipeline.py                         ← A+B+C+D+E 全流程串联
│   └── prompts/                            ← system / daily_report / classify
│
├── scripts/
│   └── com.emma.org-future-insights.bailian.plist  ← launchd 06:30
│
├── daily-reports/                          ← *-auto.md (自动) + *-visual.md (可视化) + *-pm.md (模式 B 精读)
├── companies/  research/  cases/  readings/  dictionary/  dashboard/  events/
│                                           ← 每个板块下 auto-YYYY-MM-DD.md (百炼分流)
└── ~/org-future-insights/                  ← 运行时（非工作区）
    ├── daily-raw/YYYY-MM-DD.json
    └── daily-raw/_logs/
        ├── bailian.cost.log                ← token 用量
        ├── bailian.pipeline.log            ← pipeline 总账
        └── YYYY-MM-DD-audit.json           ← 质量审计结果
```

---

## 六、运营成本（v0.4.0 实测）

| 项 | 频次 | tokens (in/out) | 单次 ¥ |
|---|---|---|---|
| 自动日报 (A) | 1 次/日 | 12.6k / 1.9k | 0.049 |
| 自动分流 (B) | 4 batch/日 | 9k / 2.8k 合计 | 0.048 |
| 可视化 (C) | 1 次/日 | 本地模板 | 0 |
| 侧边栏 (D) | 1 次/日 | 本地文件 | 0 |
| 审计 (E) | 1 次/日 | 本地 regex | 0 |
| **每日合计** | — | — | **¥0.10** |
| **每月合计** | — | — | **¥3.0** |

模式 A 实时查询 ≈ ¥0.01–0.05/次（用 qwen-plus 更便宜）；模式 B 精读补刀 ≈ ¥0.10/次。

---

## 七、边界声明

- **不能**：脱离 Qoder 自动跑模式 A / B / C（这三个需要 Agent 在场）
- **能**：模式 D 完全脚本化，launchd 已自动每天跑一遍（含 C/D/E）
- **能**：百炼失败时降级 — pipeline.py 退出码 2 表示部分失败，可视化/审计仍会尝试执行
- **能**：审计未通过时自动记录日志，不阻塞站点展示
- **承诺**：所有 raw 数据留本地，仅 token 文本走百炼 API（不存任何 PII）

详细决策理由见 [DESIGN-NOTES.md](DESIGN-NOTES.md)。

---

## 八、版本

| 版本 | 日期 | 关键变更 |
|---|---|---|
| v0.1 | 2026-06-14 上午 | 初版：3 模式 + launchd 抓取 + 9 类提示词模式继承 hr-role-insight v0.4 |
| v0.2 | 2026-06-14 下午 | HR 内容门户 8 板块上线（companies/research/cases/readings/dictionary/dashboard/events + daily）|
| v0.3.0 | 2026-06-14 晚 | 接入阿里云百炼 qwen-max；新增模式 D 手动 pipeline；模式 B 从“生成”转为“审阅/补刀”；launchd 升级 06:30 自动跑百炼 |
| **v0.5.0** | **2026-06-19** | **新增模式 F（--action 行动计划）：基于日报信号自动生成 HRBP 专属行动计划 + Excel 多 Sheet 导出 + Canvas 看板；中国映射严格溯源规则；SKILL description 重写触发更精准；完成后选项升级为 4 项** |
