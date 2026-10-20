# product-diagram-generator · 产品流程图生成器

产品经理的图表达 Agent Skill：把**说不清的多角色业务**和**讲不透的产品架构**，压成一张评审会上讲得透的图。输入大白话，输出规范源码与矢量文件。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 解决什么问题

业务一复杂，文档写几千字，评审会上还是讲不清「谁在什么时候做什么、超时走哪条分支、钱在哪一步切换」。架构一摊开，模块摆得到处都是，说不出哪层定规则、哪层只是转接。

这个 Skill 输入大白话（角色、主干、异常 / 模块、分层），输出可维护的源码：Mermaid（纯文本、能 diff）+ draw.io 矢量文件（可拖拽精修），外加一段只讲图上看不出的信息的分层说明。

## 能力

| 图型 | 输入 | 产出 |
|---|---|---|
| **跨角色泳道图** | 角色清单、主干步骤、异常分支 | Mermaid `flowchart` + `subgraph` |
| **主干流程图 / 状态机图 / 时序图** | 步骤序列、状态集合、调用序列 | 对应 Mermaid 语法 |
| **分层架构图** | 功能模块清单、分层判断 | `.drawio`（层带 + 模块 + 决策带） |
| **分层说明** | 已定稿的图 | 角色层 / 流程层 / 系统层 / 边界 四段文字 |

**不做**：编造业务里不存在的角色与分支；输出位图成品（PNG 请用 draw.io 或 mermaid.live 导出）。

## 三个卡点

1. **结构确认**——角色 / 主干 / 异常三份清单写全之前，不出图
2. **异常闭合**——每条异常都有触发条件、处理方、结果，且在图上有出口
3. **校验通过**——语法脚本 PASS + 结构自检 + 渲染预览人眼核对，三段缺一不可

## 安装

> 📖 **图文操作手册**：见 [docs/manual.html](docs/manual.html)（含 5 种安装方式、需求模板、三个卡点的应答话术与 FAQ），PDF 版随发布附上。

**WorkBuddy 用户（推荐）**：把仓库地址发给 AI，说「帮我把这个仓库安装到技能目录」；或自己执行：

```bash
git clone git@github.com:JS-Carrot/product-diagram-generator.git \
  ~/.workbuddy/skills/product-diagram-generator
```

仓库根目录就是技能本体，克隆下来名字对得上就能被扫描到，不需要再搬一层。

装完自检：对 AI 说「画个泳道图」，它先反问你角色 / 主干 / 异常，说明装对了；直接开始编节点就是没装对。

**其他支持 Agent Skills 的运行时**：克隆到对应技能目录即可，技能入口是 `SKILL.md`。

## 快速开始

```text
用 $product-diagram-generator，画一张【换机与旧机回收】跨角色泳道流程图。
角色：客户、运维、物流承运商、平台系统。
必须覆盖：正常换机链路（申请 → 出库 → 签收 → 寄回 → 检测 → 擦除 → 关单），
以及库存缺货、旧机逾期未寄回、检测不合格三条异常分支。
输出 Mermaid 源码 + 分层说明，另出一份可拖拽的 .drawio。
```

画分层架构图：

```text
用 $product-diagram-generator，给【车载数据迁移平台】画一张产品功能架构图。
分层：用户端、业务应用层、核心业务域、中台服务集成层、基础与数据层。
每层先给我模块清单让我确认，再出 drawio 矢量图。
```

更多提示词见 [examples/](examples/README.md)。

## 目录结构

```text
.
├── SKILL.md                        # 技能入口：分流规则 + 七个 Stage + 三个卡点
├── README.md
├── LICENSE
├── docs/manual.html                # 产品经理视角的图文操作手册
├── references/
│   ├── structure-extraction.md     # 结构抽取：角色 / 主干 / 异常
│   ├── diagram-selection.md        # 图型选型（含两套架构层序）
│   ├── mermaid-rules.md            # Mermaid 语法与禁用写法
│   ├── drawio-rules.md             # drawio 画法：泳道图 + 分层架构图两套坐标算法
│   ├── layering-notes.md           # 分层说明：流程图版 / 架构图版
│   └── verification.md             # 三段校验：语法 → 结构 → 视觉
├── assets/
│   ├── swimlane-template.mmd       # Mermaid 起手模板
│   ├── swimlane-template.drawio    # 泳道图骨架
│   └── architecture-template.drawio# 架构图骨架（含决策带）
├── examples/                       # 两个完整案例（同一业务线，流程视角 + 结构视角）
└── scripts/
    ├── check_mermaid.py            # Mermaid 自检
    └── check_drawio.py             # drawio 校验（含连线穿框/交叉检查）+ SVG 预览渲染
```

## 自检

```bash
python3 scripts/check_mermaid.py examples/device-swap-swimlane.md
python3 scripts/check_drawio.py examples/device-swap-swimlane.drawio --preview
python3 scripts/check_drawio.py examples/vehicle-data-migration-architecture/architecture.drawio --preview
```

`check_drawio.py --preview` 会在同目录生成 `-preview.svg`，用浏览器打开即可核对排版。两个脚本只依赖 Python 3 标准库，无需安装任何包。

## 已知边界

Mermaid **没有原生 swimlane 语法**，本 Skill 用 `subgraph` 模拟：泳道只能整块堆叠，同一角色无法在不同阶段出现两次。需要严格泳道对齐或投屏讲解时用 draw.io 版本（原生 swimlane 容器）。这一点会在交付时如实说明。

架构图默认**不画依赖箭头**：层带自上而下堆叠本身就是依赖方向。要强调某条数据流或标出反向依赖（架构异味）时才加线。

## License

MIT — 见 [LICENSE](LICENSE)。
