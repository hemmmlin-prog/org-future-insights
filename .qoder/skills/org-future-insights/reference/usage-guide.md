# org-future-insights · 最大化使用指南

> 速卖通 HRBP Leader 专属 · 从"信号"到"行动"的完整工作流

---

## 一、三大核心节奏

### 🌅 每天早上（2 分钟）

| 你说什么 | SKILL 做什么 |
|---|---|
| "今天的日报" | 如果 launchd 漏跑，自动兜底生成全流程 |
| "今天有什么启发" | 读完 auto 版后，直接帮你提炼对供给/供应链的启发 |

如果 auto 版已生成（正常情况），直接浏览器打开：
```
http://localhost:3000/#/daily-reports/YYYY-MM-DD-visual
```

---

### 📋 每周一（10 分钟）—— 最高价值时刻

**第一步：精读版**
```
/org-future-insights --review
```
→ 出一份严格溯源的 PM 精读版（反方对冲 + 真实中国映射）

**第二步：行动计划**
```
/org-future-insights --action
```
→ 自动生成本周行动计划 + Excel（含 HRG 摸底作业模板）

> 这两步组合是你最大的杠杆：每周花 10 分钟，拿到一份有信号支撑的行动清单 + 给团队的标准作业。

---

### 🔍 随时深挖（按需）

| 场景 | 怎么说 |
|---|---|
| 想深挖某个话题 | "AI Agent 对供应链岗位的影响" / "多 Agent 协作下绩效怎么算" |
| 准备跟 VP 汇报 | `/org-future-insights --share 2026-06-19` → 打包 |
| auto 版质量有疑问 | `/org-future-insights --audit` → 看 6 项审计结果 |
| 想看某条信号的原始出处 | 直接问"信号 1 的原文是哪篇" → 帮你查 raw |
| 想对比历史趋势 | `/org-future-insights --action 2026-06-14` → 跑一周前的行动计划 |

---

## 二、最佳实践 Checklist

```
□ 周一：--review + --action（精读+行动计划，10min）
□ 周三：浏览 visual 版，看有没有新的强信号冒出来
□ 周五：收 HRG 摸底结果，周度 Excel 自动生成（18:00 launchd）
□ 月底：积累 4 周行动计划，提炼成给 VP 的月度 one-pager
□ 季末：回顾 12 周信号趋势，写入 Q+1 OKR
```

---

## 三、自动化节奏一览

| 时间 | 自动做什么 | 产物位置 |
|---|---|---|
| 每天 06:00 | 抓取 19 源 RSS/API | `daily-raw/YYYY-MM-DD.json` |
| 每天 06:30 | pipeline 全流程（日报+分流+可视化+侧边栏+审计）| `daily-reports/` + 8 板块 |
| 每周五 18:00 | 调百炼生成周度行动计划 Excel | `weekly-actions/YYYY-WNN-行动计划.xlsx` |

手动兜底（Mac 睡眠/百炼 quota 不够时）：
```
/org-future-insights --daily
```

---

## 四、六种模式速查

| 模式 | 命令 | 一句话说明 |
|---|---|---|
| A. 实时查询 | `/org-future-insights "主题"` | 按需深挖某个话题，500-1500 字 |
| B. 审阅补刀 | `/org-future-insights --review` | 严格溯源 PM 精读版 |
| C. 分享导出 | `/org-future-insights --share` | 打包 / 剪贴板 / Docsify 直链 |
| D. 一键日报 | `/org-future-insights --daily` | 全流程兜底 |
| E. 质量审计 | `/org-future-insights --audit` | 6 项自检报告 |
| F. 行动计划 | `/org-future-insights --action` | HRBP 行动计划 + Excel + Canvas |

---

## 五、进阶技巧

### 1. 历史对比
```
/org-future-insights --action 2026-06-14
```
跑一周前的行动计划，对比信号演变方向。

### 2. 主题追踪
连续几天问同一个话题（如"共生岗位设计"），SKILL 会在知识包里逐渐积累深度。

### 3. 分享给团队
`/org-future-insights --share` 生成的 Docsify 链接可以直接发给 HRG 团队看——站点内容是**中性的行业情报**，不含你的角色、判断和行动决策。

### 4. 定制化追问
看完 auto 版后，可以直接追问：
- "把信号 1 的反方再加一条 NBER 实证"
- "这条对我们选品策略团队意味着什么"
- "帮我写个 3 句话的消息发给业务 VP"

### 5. 周度 Excel 即时生成
不等周五自动跑？随时手动：
```
/org-future-insights --action
```
会同时生成 Canvas 看板 + Excel 文件。

### 6. 省钱模式
```
/org-future-insights --daily --model qwen-plus
```
日报生成成本从 ¥0.10 降到 ¥0.02，质量略有下降但足够日常浏览。

---

## 六、隐私与分享策略

| 内容 | 谁能看 | 说明 |
|---|---|---|
| Docsify 站点 | 团队所有人 | 中性行业情报，无角色信息 |
| Excel 行动计划 | 只有你 | 含速卖通/HRBP Leader 视角 |
| Canvas 看板 | 只有你（Qoder IDE） | 含角色信息 |
| `.qoder/skills/` | 不会展示 | 隐藏目录 |

**定位建议**：对外把站点包装为"HR 团队共享的行业趋势情报站"——

- 对上（VP/HRD）→ 展示你的信息嗅觉
- 对下（HRG）→ 提供素材输入
- 对平级 → 展示合作价值

**判断和行动留在你的 Excel 里。**

---

## 七、成本概览

| 项目 | 频次 | 单次成本 | 月度成本 |
|---|---|---|---|
| 每日 pipeline | 1次/天 | ¥0.10 | ¥3.0 |
| 周度行动计划 | 1次/周 | ¥0.03 | ¥0.12 |
| PM 精读补刀 | 按需 | ¥0.10/次 | ~ ¥0.40 |
| 实时查询 | 按需 | ¥0.01-0.05/次 | ~ ¥0.50 |
| **合计** | — | — | **≈ ¥4/月** |

---

## 八、一句话总结

> **周一 `--review` + `--action` 是你的核心动作**，其余时间只需浏览 visual 版 + 按需深挖。每周投入 15 分钟，产出是一份有信号支撑的行动清单 + 给团队的标准化作业。
