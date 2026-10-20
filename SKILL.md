---
name: product-diagram-generator
description: |
  把多角色业务链路与产品架构，压成一张评审会上讲得透的图。
  输入大白话（谁参与、主干怎么走、哪里会出岔子），输出规范 Mermaid 源码 + 可选 draw.io 矢量文件，并附一段分层说明。
  覆盖五类图：跨角色泳道图、主干流程图、状态机图、时序图、分层架构图（产品功能架构）。
  触发词：画流程图、泳道图、跨角色流程、业务链路图、状态机、时序图、框架图、架构分层图、功能架构图、drawio 文件。
  不编造业务里不存在的角色与分支；结构没确认不出图；校验没过不交付。
version: "2.0"
updated: "2026-10-20"
---

# 产品流程图生成器（product-diagram-generator）

一段说不清的多角色业务，压成一张评审会上讲得透的图。

输入是**大白话**：谁参与、主干怎么走、哪里会出岔子。
输出是**可维护的源码**：Mermaid（默认，纯文本、能 diff）+ draw.io 矢量文件（要拖拽精修时），外加一段只讲图上看不出的信息的**分层说明**。

本文件里的 **Stage** 指技能自身的执行阶段，和业务图里的「步骤」不是一回事，读的时候别混。

## 能做什么

| 图型 | 什么时候用 | 需要你给的素材 | 产出 |
|---|---|---|---|
| **泳道图** `swimlane` | 角色 ≥2，且有交接、超时、驳回 | 角色清单、主干步骤、异常情况 | Mermaid `flowchart` + `subgraph` 分泳道 |
| **主干流程图** `flow` | 单角色，或纯系统内部串行 | 步骤序列、判断条件 | Mermaid `flowchart` |
| **状态机图** `state` | 单据/设备/工单的状态流转 | 状态集合、触发事件、守卫条件 | Mermaid `stateDiagram-v2` |
| **时序图** `sequence` | 强调系统间调用先后与返回 | 参与方、消息序列 | Mermaid `sequenceDiagram` |
| **分层架构图** `arch` | 讲清「系统由哪几层组成、谁依赖谁」 | 功能模块清单、分层判断 | draw.io 矢量文件（层带 + 模块）+ 分层说明 |
| **分层说明** `layering` | 总是附带 | 已定稿的图 | 角色层 / 流程层 / 系统层 / 边界 四段文字 |

**不做什么**：

- 不编造业务里不存在的角色、状态、分支。缺信息就问，不脑补。
- 不出位图成品。本技能给的是源码与矢量文件，PNG 请用 draw.io 或 mermaid.live 导出，别在这里绕。
- 不用装饰性插画替代逻辑结构。图的价值在信息密度，不在好看。

## 开工前先读

必读三份：

1. 本文件
2. [references/structure-extraction.md](references/structure-extraction.md) —— 从大白话抽出角色 / 主干 / 异常的方法与追问清单
3. [references/mermaid-rules.md](references/mermaid-rules.md) —— Mermaid 规范语法与禁用写法

按任务再取：

- 图型拿不准 → [references/diagram-selection.md](references/diagram-selection.md)
- 要出 `.drawio` → [references/drawio-rules.md](references/drawio-rules.md)
- 要写分层说明 → [references/layering-notes.md](references/layering-notes.md)
- 交付前怎么验 → [references/verification.md](references/verification.md)
- 起手抄模板 → [assets/](assets/) 下的 `.mmd` 与 `.drawio`
- 看完整实例 → [examples/README.md](examples/README.md)

## 三个卡点

这三处不过，不往下走。宁可停下来问，也不要产出一张需要重画的图。

| 卡点 | 位置 | 判据 |
|---|---|---|
| **G1 结构确认** | Stage 1 结束 | 角色 / 主干 / 异常三份清单写全，异常每条都有触发条件、处理方、结果 |
| **G2 异常闭合** | Stage 3 结束 | 每条异常都落到了图上，且都有出口（回流某步 或 终止），没有「异常处理中」这种糊过去的节点 |
| **G3 校验通过** | Stage 6 结束 | 语法校验 PASS，结构自检清单全绿，视觉预览人眼过了一遍 |

## 分流规则

1. 给了**多个角色**，且提到交接/超时/驳回 → `swimlane`
2. 只给一串步骤、没有角色概念 → `flow`，别硬套泳道
3. 说的是「一个单据从 A 状态到 B 状态」→ `state`
4. 强调「谁先调谁、什么时候返回」→ `sequence`
5. 说「系统分几层」「功能架构」「框架图」「讲给老板听的整体结构」→ `arch`
6. 说「要能拖拽改」「要 draw.io 文件」「要放进 Obsidian」→ 结构定稿后追加 `drawio` 出口
7. 只说「画个流程图」但没给素材 → 按追问清单一次问 1–3 个高优先级问题，别一次甩十个

**顺序固定**：先定结构，再选图型，最后出源码。结构没定就出图 = 重画。

## 七个 Stage

### Stage 1 · 结构抽取

按 [references/structure-extraction.md](references/structure-extraction.md) 出三份清单，先不画图：

```text
角色：客户 / 运维 / 物流承运商 / 平台系统
主干：每条写成「谁 → 做什么 → 交给谁」
异常：每条写成「触发条件 → 处理方 → 结果」
```

关键判断：**异常不是补充项，是主干的一部分**。只有正常路径的图，评审时被研发问一句就穿。

### Stage 2 · 图型选型

按分流规则选。泳道只在「角色 ≥2 且存在跨角色交接」时用；单角色硬套泳道只会把图撑宽。

### Stage 3 · 出 Mermaid 源码

严格按 [references/mermaid-rules.md](references/mermaid-rules.md)。四条最常踩的：

- 每个角色一个 `subgraph`，泳道名用中文角色名
- 节点 ID 一律 ASCII（`C1`、`O2`、`S1`），中文只写进 `[]` 标签里
- 标签含 `()`、`[]`、`{}`、`、`、`:` 时整体加双引号：`C1["提交换机申请（7 天内）"]`
- 判断用 `{}`，起止用 `([])`，异常用虚线 `-.->`，主干用实线 `-->`

### Stage 4 · 写分层说明

按 [references/layering-notes.md](references/layering-notes.md) 写四段。流程图版和架构图版的四段内容不同，别套错。
每一段只讲**图上看不出来的信息**（谁负最终责任、哪一步不能自动化、哪条分支不回流）。复述箭头等于没写。

### Stage 5 · drawio 出口（按需）

用户要可拖拽源文件时，按 [references/drawio-rules.md](references/drawio-rules.md) 生成 `.drawio`：

- **泳道图**：每个角色一个原生 swimlane 容器，节点是泳道的子元素
- **分层架构图**：每条层带一个 swimlane，模块横向均分，附带一条「已定稿决策」带

### Stage 6 · 校验

按 [references/verification.md](references/verification.md) 跑三段：语法 → 结构 → 视觉。

```bash
python3 scripts/check_mermaid.py path/to/diagram.mmd
python3 scripts/check_drawio.py path/to/diagram.drawio --preview
```

视觉那一步不能省：把 `.drawio` 渲染成 SVG 再截图看一眼，压字、溢出、层带错位都只有肉眼能发现。

### Stage 7 · 交付

```text
图型：跨角色泳道图（Mermaid flowchart TD）
泳道：客户 / 运维 / 物流承运商 / 平台系统
分支：主干 1 条 + 异常 3 条
产物：<路径>.mmd（源码）、<路径>.md（含分层说明）、<路径>.drawio（可选）
校验：check_mermaid.py PASS / check_drawio.py PASS，无压字与溢出
怎么看：Obsidian 装 Diagram 插件双击预览；draw.io 桌面版打开可拖拽
```

## Mermaid 泳道的真实边界

Mermaid **没有原生 swimlane 语法**。通行做法是用 `subgraph` 模拟，有两个硬限制：

1. 泳道只能**整块堆叠**，做不到「同一角色在不同阶段出现两次」的经典泳道排布
2. 泳道内无法强制水平流向，跨泳道箭头由布局引擎决定

所以：

- 角色少、交接简单 → Mermaid 够用，**优先用它**（纯文本、可 diff、可版本管理）
- 角色多、要严格对齐、要投屏讲 → 出 draw.io，它有原生 swimlane 容器

**不要向用户承诺「Mermaid 能画出标准泳道图」。** 先讲清差异，再给建议。

## 不可破的线

- 图里不出现业务里不存在的角色、状态、分支。缺信息就问，不脑补。
- 不交付只有正常路径的流程图。
- 节点标签 ≤18 个汉字；超了拆节点，或把细节挪进分层说明。
- 一张图节点 ≤25 个；超了拆图，不硬塞。架构图例外，模块按层算，单层 ≤8 个。
- 节点 ID 一律 ASCII，中文只出现在标签和泳道名里。
- 产物落在任务归属目录；没有归属时放 `outputs/`，不要把源码当正文塞进知识库。
- 语法校验没过不交付。

## 交付前自检

- 每个角色是否都有独立泳道，泳道里是否只放该角色的动作？
- 主干是否从头走到尾，无断链、无孤岛？
- 每条异常是否都标了触发条件？超时、拒收、并发冲突这类是否都有出口？
- 跨泳道交接点是否明确（谁交给谁、交的是什么）？
- 虚线是否只用于异常和可选路径？
- `subgraph` 与 `end` 是否配平？`check_mermaid.py` 是否 PASS？
- 架构图的层与层是否只向上依赖，没有反向箭头？
- 分层说明是否只讲图上看不出的信息？
- 是否如实说明了 Mermaid 泳道的限制？

## 产出口径

```text
已生成 <图型>，放在：<路径>
泳道：<角色列表>；分支：主干 <n> 条 + 异常 <m> 条
重点标注：<最关键的异常分支或系统边界>
验证：语法 PASS、结构自检全绿、视觉预览已核对
```
