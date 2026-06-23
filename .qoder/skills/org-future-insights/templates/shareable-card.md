# 模板 · 分享卡片（模式 C · v0.2 预留）

> **状态**：v0.1 仅为占位，v0.2 才会真正实现
> **目的**：为未来的"一键分享 / 公开 URL / 微信公众号 / PDF 导出" 留模板

---

## v0.1 当前实现（轻量替代）

当用户敲 `/org-future-insights --share <topic-or-date>` 时，SKILL 应：

1. 提示用户："分享功能在 v0.2 实现，当前提供以下 3 种轻量替代："
   - **A.** 复制目标 MD 文件路径到剪贴板（用户自行邮件 / IM 发送）
   - **B.** 把目标 MD + 引用图片打包成 ZIP（用 macOS `zip` 命令）
   - **C.** 提示用户 Docsify 站点已可访问 `http://localhost:3000/#/<path>`（局域网内分享）

2. 询问用户偏好哪种方式，按需执行

---

## v0.2 规划：完整分享卡片

### 卡片结构

```markdown
# [报告标题] · [日期]

> **作者**：[Emma 的 HR 视角]
> **来源**：org-future-insights v0.x
> **分享 URL**：https://org-evolution.vercel.app/#/daily-reports/YYYY-MM-DD

---

## 核心摘要（30 秒读完）
[3-5 句话浓缩]

## 关键数据
- 数据点 1
- 数据点 2
- 数据点 3

## 反方观点
[1 条最重要的反方]

## 我的判断（HR 视角）
[Emma 个人解读 — 需要用户在生成时填入]

---

> 📨 转发请保留来源链接 | 📧 联系 Emma：xxx@xxx.com
```

### 三种导出格式（v0.2 实现）

| 格式 | 用途 | 工具 |
|---|---|---|
| **公开 URL** | 同事 / LinkedIn / 知识星球 | vercel-deploy SKILL |
| **微信公众号 MD** | 国内分享 | 自定义脚本（去除 emoji + 加微信样式）|
| **PDF** | 高保真存档 / 邮件附件 | macOS `cupsfilter` 或 pandoc |

---

## v0.2 待实现脚本清单

```
scripts/
├── share_to_vercel.sh        # 调用 vercel-deploy SKILL，生成公开 URL
├── share_to_wechat.py         # MD 转换为微信公众号格式
├── share_to_pdf.sh            # MD 转 PDF
└── archive_zip.sh             # 打包 MD + 图片为 ZIP
```

---

## 触发开发的条件

只有当用户**第二次**敲 `/org-future-insights --share` 并主动要求"想分享给同事"时，才考虑触发 v0.2 开发。

> **决策依据**：DESIGN-NOTES §9 路线图 — 模式 C 不阻塞主流程
