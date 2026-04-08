---
title: "面向自治代理的欧盟 AI 法案合规性"
description: "如何使用 CORTEX-Persist 构建原生符合欧盟 AI 法案第 12 条的 AI 代理。"
date: 2026-04-07
---

# 面向自治代理的欧盟 AI 法案合规性

到 2026 年，监管环境要求绝对的可追溯性。

### 第 12 条：记录保存
欧盟 AI 法案要求高风险 AI 系统严格保存记录。CORTEX-Persist 原生提供 `ComplianceTracker`。

* **加密事件账本：** 每次工具执行都会签名到 Merkle 树中。
* **防篡改历史：** SQLite-vec 哈希链确保代理的时间线在执行后无法更改。

使用 CORTEX，在欧洲市场部署合法的自治系统。
