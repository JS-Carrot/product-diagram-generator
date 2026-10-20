# draw.io 生成规则

Mermaid 没有原生泳道容器，分层架构图更是画不了。要「可拖拽精修」「进 Obsidian 双击打开」「投屏讲解」「交付给客户」时，出 `.drawio`。

两种图型两套坐标算法，别混用：**泳道图按阶梯排**，**分层架构图按层带排**。

## 一、文件骨架

```xml
<mxfile host="app.diagrams.net" agent="product-diagram-generator" version="24.0.0" type="device">
  <diagram id="swap-swimlane" name="换机泳道图">
    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1"
                  tooltips="1" connect="1" arrows="1" fold="1"
                  page="1" pageScale="1" pageWidth="1600" pageHeight="1000"
                  math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- 内容写在这里 -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**必须保留 `id="0"` 和 `id="1"`**，缺一个文件打不开。

## 二、泳道图：每角色一条泳道

### 泳道容器

```xml
<mxCell id="lane_cust" value="客户"
        style="swimlane;horizontal=1;startSize=110;fillColor=#EAF2FF;strokeColor=#3B82F6;fontColor=#1E3A8A;fontStyle=1;fontSize=13;"
        vertex="1" parent="1">
  <mxGeometry x="40" y="90" width="2380" height="200" as="geometry" />
</mxCell>
```

| 属性 | 含义 |
|---|---|
| `horizontal=1` | 横向泳道：标题竖排在左，内容往右排。跨职能流程图用这个 |
| `horizontal=0` | 纵向泳道：标题横排在上，内容往下排 |
| `startSize` | 标题栏宽度（横向）/高度（纵向） |
| `fillColor` | 泳道底色，按角色语义取浅色 |

### 横向泳道的坐标

- 所有泳道同宽（如 2380），`x` 相同，只改 `y`
- `y(n+1) = y(n) + height(n) + 16`
- 节点 x 从 `startSize + 24` 起算

### 节点坐标：列号决定 x

先给主干的每个动作编一个**列号**，再算像素。这样跨泳道的交接点能上下对齐，箭头接近垂直，图才不乱。

```text
x = 40 + startSize + 24 + 列号 × 200      （列间距 = 200 - 150 = 60px）
y = 泳道 y + 48                           （A 行：主干）
y = 泳道 y + 152                          （B 行：分支，泳道高度需 ≥230）
```

**间距硬约束**：相邻节点间隙 ≥60px、行间隙 ≥60px。间隙是给箭头线段和边标签留的——
小于 40px 时「有货 / 缺货」这类 2 字标签会盖住框边，箭头几乎没有可见线段。

列号允许半列（`3.5`），用来放不占主干位置的分支节点。

```xml
<mxCell id="C1" value="提交换机申请"
        style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;fillColor=#FFFFFF;strokeColor=#3B82F6;fontColor=#1E3A8A;fontSize=12;"
        vertex="1" parent="lane_cust">
  <mxGeometry x="134" y="44" width="150" height="44" as="geometry" />
</mxCell>
```

**关键**：子节点坐标相对泳道原点，`parent` 指向泳道 ID。横向泳道里 `x` 必须 ≥ `startSize`，否则会压住左侧标题栏。

### 常用节点样式

| 类型 | style 片段 |
|---|---|
| 普通步骤 | `rounded=1;whiteSpace=wrap;html=1;arcSize=10;` |
| 起止 | `rounded=1;arcSize=50;whiteSpace=wrap;html=1;` |
| 判断 | `rhombus;whiteSpace=wrap;html=1;` |
| 系统动作 | `rounded=0;whiteSpace=wrap;html=1;fillColor=#F3F4F6;strokeColor=#6B7280;` |
| 异常分支 | `rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF4E5;strokeColor=#F59E0B;dashed=1;` |
| 失败/终止 | `rounded=1;whiteSpace=wrap;html=1;fillColor=#FDECEC;strokeColor=#EF4444;` |

### 连边

连边是根单元格的子元素（`parent="1"`），不挂在泳道下：

```xml
<mxCell id="e1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;strokeColor=#1F2937;"
        edge="1" parent="1" source="C1" target="S1">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

规则：

- 主干：实线，`strokeColor=#1F2937`
- 异常：虚线，`dashed=1;strokeColor=#F59E0B;`，标签写进 `value`
- 失败/终止：虚线，`dashed=1;strokeColor=#EF4444;`
- `source`/`target` 必须指向存在的 ID，**悬空引用会让文件打不开或报错**
- 每条边 ID 唯一（`e1`、`e2`…）

### 连线锚点与标签位置（必写）

每条边都要写显式锚点 `exitX/exitY`（出边）和 `entryX/entryY`（入边），取值 0~1，
`exitDx=0;exitDy=0;entryDx=0;entryDy=0` 一并带上。四个标准锚点：

| 记号 | 分数 | 含义 |
|---|---|---|
| T | (0.5, 0) | 顶边中点（菱形=上顶点） |
| B | (0.5, 1) | 底边中点（菱形=下顶点） |
| L | (0, 0.5) | 左边中点（菱形=左顶点） |
| R | (1, 0.5) | 右边中点（菱形=右顶点） |

选边原则（`check_drawio.py` 渲染器与 draw.io 都按锚点走线）：

- 目标在右侧且横向余量 ≥30px：`R→L`（Z 形）
- 目标在右下/右上但列间隙窄（<30px）：纵向优先出肘，`B→L` 或 `T→L`
- 同列上下直连：下行 `B→T`，上行 `T→B`（**上行必须从顶边出**，否则线会穿过源框）
- 目标与源横向区间重叠：竖直通道绕行 `B→T` / `T→B`
- **往返线对**（A→B 与 B→A 并存）：两条边各偏一侧，如 `exitX=0.35` 与 `exitX=0.65`
- 标签默认放走线弧长中点；往返线对距离近时用 `labelT`（0=起点端 1=终点端）错开高度，
  长标签用 `<br>` 折行（html=1 下 draw.io 与渲染器都识别）
- **终态节点跟着分支走**：把「流程终止」放进触发它的分支所在的泳道、紧贴分支节点，
  而不是放到语义上"像客户"的泳道——跨泳道长线必然与相邻列的竖直连线打架
- 实在绕不开时用**固定折点**：在 `<mxGeometry>` 里写
  `<Array as="points"><mxPoint x="…" y="…"/></Array>`（画布绝对坐标），draw.io 与
  渲染器都会严格按折点走线，不依赖自动路由

不做锚点约束的后果：draw.io 自动路由会把上行线画成穿框、把通道贴在框边，
渲染预览同样出问题——这是实际踩过的坑。

### 连边几何硬校验（check_drawio.py 自动执行）

以下两条是**错误级**校验，出现即退出码 1，必须修掉才能交付：

- 连边线段穿过任何无关节点（视觉上"箭头指空"的根源）
- 两条边在内部交叉（共享端点不算）

共线重叠段记为警告。修复顺序：先调锚点改走线 → 再挪节点位置 → 最后用固定折点。

## 三、分层架构图：每层一条横带

泳道图的坐标是「阶梯」，架构图的坐标是「层带」——每条层带是一条横向 `swimlane`，模块在其中均分。

### 层带容器

```xml
<mxCell id="band_L1" value="L1  触点层"
        style="swimlane;horizontal=1;startSize=64;fillColor=#E8F1FE;strokeColor=#3B82F6;fontColor=#1E3A8A;fontStyle=1;fontSize=13;swimlaneFillColor=#FFFFFF;"
        vertex="1" parent="1">
  <mxGeometry x="124" y="88" width="1460" height="130" as="geometry" />
</mxCell>
```

层带高度 **130**，标题栏 `startSize=64`（竖排层名），模块统一 `y=39`、`h=52`。

### 模块横向均分

```text
可用宽度 = 层带宽 - startSize - 2 × 内边距(18)
模块宽   = (可用宽度 - (n-1) × 12) / n
x(i)     = startSize + 18 + i × (模块宽 + 12)
```

单层模块数建议 ≤8。超过 8 个，要么合并，要么这一层该拆。

模块标签用两行：**粗体功能名 + 小字补充**，补充里写这个模块到底管什么。

```xml
<mxCell id="L3_5" value="&lt;b&gt;计费结算域&lt;/b&gt;&lt;br&gt;&lt;font style=&quot;font-size:10px&quot; color=&quot;#6B7280&quot;&gt;计量·月结·逾期&lt;/font&gt;"
        style="rounded=1;whiteSpace=wrap;html=1;arcSize=8;fillColor=#FFFFFF;strokeColor=#E8B36A;fontColor=#1F2937;fontSize=12;spacing=4;"
        vertex="1" parent="band_L3">
  <mxGeometry x="134" y="39" width="216" height="52" as="geometry" />
</mxCell>
```

### 层序与配色

自上而下：触点层 → 应用服务层 → 核心业务域 → 中台与集成层 → 基础与数据层。

| 层 | 底色 | 描边 | 含义 |
|---|---|---|---|
| 触点层 | `#E8F1FE` | `#3B82F6` | 用户看到的一切 |
| 应用服务层 | `#E6F6F4` | `#0D9488` | 只编排，不定规则 |
| 核心业务域 | `#FDF3E3` | `#D97706` | 规则唯一归属地（暖色，视觉重心） |
| 中台与集成层 | `#EEF0FB` | `#4F46E5` | 外部系统与共享能力 |
| 基础与数据层 | `#F3F4F6` | `#6B7280` | 不承载业务语义 |

**核心域用暖色**，是为了让读者第一眼落在规则所在地。这是整张图唯一允许抢眼的部分，别在别处加颜色。

### 不画箭头

层带堆叠本身就是依赖方向。加箭头只在两种情况下：

- 要强调某条关键数据流（如「计量结果 → 计费域」）
- 出现了反向依赖（这是异味，必须显式标出来并单独说明）

### 附一条「已定稿决策」带

架构图评审时最耗时的不是看懂结构，而是**重新讨论已经定过的事**。把结论直接印在图上：

```xml
<mxCell id="dec_bg" value=""
        style="rounded=1;whiteSpace=wrap;html=1;arcSize=6;fillColor=#FFFCF4;strokeColor=#EDDFC0;"
        vertex="1" parent="1">
  <mxGeometry x="124" y="820" width="1460" height="56" as="geometry" />
</mxCell>
```

格式：左侧「已定稿 + 日期」，右侧 3–4 条一句话结论（每条 ≤22 字），一行排开。

> 这条带子是本技能的固定动作，不是可选装饰。没有它，同一张图会被反复问同样四个问题。

### 图例

底部一条浅色带，三句话解释配色规则，别写超过三行。

## 四、语义配色（与 Mermaid 版一致）

| 语义 | fillColor | strokeColor | fontColor |
|---|---|---|---|
| 起止 / 成功 | `#E9F9EF` | `#10B981` | `#065F46` |
| 角色动作 | `#FFFFFF` | `#3B82F6` | `#1E3A8A` |
| 系统 / 后台 | `#F3F4F6` | `#6B7280` | `#1F2937` |
| 异常 / 超时 | `#FFF4E5` | `#F59E0B` | `#92400E` |
| 失败 / 终止 | `#FDECEC` | `#EF4444` | `#991B1B` |

泳道底色用对应语义色的浅色版，标题文字用深色版。

## 五、校验

```bash
python3 scripts/check_drawio.py path/to/diagram.drawio            # 只校验
python3 scripts/check_drawio.py path/to/diagram.drawio --preview  # 校验 + 渲染 SVG 预览
```

脚本查：

- `id="0"` / `id="1"` 是否存在
- 所有 `parent` / `source` / `target` 是否指向存在的 ID
- ID 是否重复
- 子节点是否越出父容器
- 同层兄弟节点是否重叠
- 横向泳道里节点 `x` 是否小于 `startSize`（会压住标题栏）
- 连边线段是否穿过无关节点、两条边是否内部交叉（错误级，见上节）

渲染出的 `-preview.svg` 是**近似预览**，只用来发现排版问题（压字、溢出、层带错位），不要当成品交付。

## 六、打开方式（写进交付说明）

- **draw.io 桌面版**：双击 `.drawio` 直接开，可拖拽改
- **网页版**：拖进 <https://app.diagrams.net>
- **Obsidian**：装 draw.io Integration 插件后双击预览

顺带告诉用户：这是标准 mxGraph XML，能提交进 Git 做版本管理和评审留痕。
