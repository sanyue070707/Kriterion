# Kriterion

**多智能体选品决策系统** — 面向跨境电商卖家的产品自动评估平台。

从候选品提交到决策卡产出，自动完成快筛、三方取证、证据核验、交叉评审，替代人工 2~4 小时的跨平台数据整合。

> 可完全离线运行：无需 Docker、API Key 或模型下载，依赖仅 8 个轻量包。LLM 与检索使用内置的本地实现，数据由本地脚本生成；各组件当前的实现方式见文末「运行形态」。

---

## 快速开始

需要 Python 3.11+。**无需 Docker、无需 API Key、无需下载模型。**

```bash
pip install -e .
python -m src demo        # 引导 + 跑一次评估 + 终端打印决策卡
```

想看浏览器界面：

```bash
python -m src web         # http://127.0.0.1:8000
```

`pip install` 只装 8 个轻量依赖（fastapi / uvicorn / pydantic / pydantic-settings /
sqlalchemy / aiosqlite / langgraph / langchain-core），**不会拉取 torch、向量库或 embedding 模型**。

首次运行会自动：生成示例数据 → 建 SQLite 库 → 灌入种子数据 → 建检索索引 → 加入 3 个示例候选品。

---

## 三种示例候选品

引导阶段会注入 3 个带标签的示例候选品，覆盖三种结局：

| 候选品 | 预期结果 |
|--------|----------|
| `Sample: Clear-Compliance Bestseller` | **GO** — 无合规阻断、毛利充足 |
| `Sample: Compliance-Blocked Listing` | **NO-GO** — 命中合规阻断规则 |
| `Sample: Screening Reject (Overpriced)` | 快筛阶段直接拒绝（条件边终止，不进入取证） |

其余 500 个随机候选品可在 Web 界面下拉选择。

---

## 架构

```
候选品 → 归一化 → 快筛漏斗 → [条件边]
  ├─ 未通过 → END (rejected)
  └─ 通过 → [并行扇出]
       ├─ 趋势需求 Agent     ─┐
       ├─ 货源成本 Agent     ─┤→ 证据守门 → 决策评审 → 决策卡 → END
       └─ 合规风险 Agent     ─┘
```

用 LangGraph 编排：三个取证 Agent **并行扇出**，汇聚到证据守门节点做屏障，再串行进入评审与产出。

### 三方取证 Agent

每个 Agent 运行一份**确定性「取证清单」**（`src/agents/plans.py`）：按维度列出要调用的业务工具、如何传参、结果如何映射为证据。
每条规则执行时记录一条 `ToolCallRecord`（工具名 / 参数 / 耗时 / 结果或错误 / 跳过），即工具调用轨迹。

| Agent | 职责 | 取证工具 |
|-------|------|----------|
| 趋势与需求 | 市场需求、趋势动能、竞争度、达人活跃度 | `search_trends`、`get_category_growth`、`get_influencer_data`、`hybrid_search` |
| 货源与成本 | 供应商报价、头程费率、平台佣金、退货率、单位经济 | `get_supplier_quotes`、`get_platform_commission`、`calculate_freight`、`calculate_unit_economics_tool` |
| 合规与风险 | 商标冲突、认证缺口、政策阻断 | `check_trademark`、`check_certifications`、`check_policy_compliance`、`hybrid_search` |

**降级是一等公民**：某条规则的前提无法满足（例如拿不到供应商报价就无法计算单位经济）会抛 `SkipStep`，
被记录为「跳过」，并产出一条低置信度的「数据缺口」证据 —— 而不是静默消失或崩溃。

> 工具选择目前由确定性清单驱动，保证每次运行可复现；若要改为由模型自主选择，
> `src/agents/base.py` 标注了替换位置，返回结构不变。

### 证据账本

**每个业务数字都绑定来源**：来源工具、原始地址（如 `mockdb://supplier_quotes?category=beauty&source_country=CN`）、
抓取时间、有效期、置信度（由样本量推导，而非恒定的 0.8）。

证据守门节点逐条校验并剔除无来源数字，产出守门报告（通过 / 剔除 / 低置信 / 过期计数）—— 这是「从流程上约束模型生成业务数据」的落地。

### 决策评审与七维打分

决策评审 Agent 汇总三方证据，完成交叉质证与裁决。**分数与裁决是确定性计算**（`src/decision/scorer.py`、`verdict.py`），
LLM 只负责在算好的数字之上渲染叙事（grounded narrative）—— 决策不依赖模型发挥。

七维权重（合计 1.0）：

| 维度 | 权重 | 证据来源 |
|------|------|----------|
| cost_margin | 0.25 | 净/毛 margin |
| market_demand | 0.20 | 搜索量 |
| compliance_risk | 0.20 | 阻断规则、商标冲突、政策警告 |
| competition | 0.10 | 活跃卖家数 |
| supply_stability | 0.10 | 供应商数量 |
| trend_momentum | 0.10 | 类目同比增速 |
| return_rate | 0.05 | 平台典型退货率 |

裁决规则：命中合规阻断 / 综合分 < 4.0 / 毛利不足 → **No-Go**；综合分 ≥ 7.0 且无阻断且毛利达标 → **Go**；其余 → **Watch**。

### 单位经济模板

按平台（TikTok Shop / Shopee）抽象可配置的成本模板（`src/config/platform_profiles.py`）：佣金档位、
支付处理费、达人佣金区间、退货率、最低可行毛利、必填成本项与敏感性轴。P&L 逐项拆解：货品成本、头程、
平台佣金、支付费、达人佣金、包装、进口关税、退货损耗。

---

## 配置

| 环境变量 | 默认 | 说明 |
|----------|------|------|
| `LLM_PROVIDER` | `mock` | `mock` 为内置的本地确定性模型；`real` 需安装 `.[real-llm]` extra 并配置 `LLM_API_KEY` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./kriterion.db` | 本地 SQLite，自动建表 |
| `AUTO_BOOTSTRAP` | `true` | 启动时自动准备数据/建库/建索引 |

---

## 项目结构

```
src/
├── main.py            # FastAPI 入口 + Web UI
├── cli.py             # kriterion bootstrap | demo | web
├── bootstrap.py       # 幂等引导：数据 → 建库 → 种子 → 索引 → 示例候选
├── console.py         # 终端输出编码兜底（中文 Windows 安全）
├── config/            # 配置 + 平台经济模板
├── agents/            # 三个取证 Agent + 评审 Agent + 取证清单 + 提示词
├── graph/             # LangGraph 工作流：State / 节点 / 编排
├── tools/             # 业务工具 + provenance 来源标识
├── evidence/          # 证据账本 + 守门 + 合并
├── decision/          # 七维打分 + 裁决 + 单位经济 + 决策卡
├── screening/         # 归一化 + 快筛漏斗
├── rag/               # 纯 Python BM25 检索 + 元数据过滤
├── db/                # SQLAlchemy ORM + 仓储层
├── llm/               # 角色化 LLM 工厂（本地确定性实现）
├── service/           # 评估服务（CLI 与 API 共用）
└── web/index.html     # 单页 Web 界面
scripts/               # 示例数据生成 / 数据库种子
data/                  # 生成的示例数据（不入库）
tests/                 # 单元测试（零外部依赖）
```

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/candidates` | 提交候选品 |
| GET | `/api/v1/candidates` | 列出候选品 |
| POST | `/api/v1/workflow/run` | 触发评估工作流 |
| GET | `/api/v1/workflow/{id}/status` | 查询工作流状态与进度 |
| GET | `/api/v1/runs/{id}` | 单次运行详情：决策卡 + 证据账本 + 工具轨迹 |
| GET | `/api/v1/decisions` | 列出决策卡（支持 `?run_id=` 过滤） |
| GET | `/health` | 健康检查 |

交互式文档：`http://127.0.0.1:8000/docs`

---

## 测试

```bash
pytest -q
```

全部为纯逻辑单测（七维打分与裁决、证据守门、快筛、单位经济、工作流编排、取证清单执行器、BM25 检索、LLM 分派），零外部依赖。

---

## 运行形态

为便于零配置运行与复现，以下组件使用本地实现。核心架构（LangGraph 状态编排、三方并行扇出、
证据账本与守门、七维打分、平台单位经济模板）不因实现形态而改变。

| 本仓库 | 生产部署 |
|--------|----------|
| 内置本地 LLM（确定性叙事） | Qwen / 真实模型 + Structured Output |
| 纯 Python BM25 检索 | BGE-M3 + Milvus 稠密检索 + BM25 + bge-reranker 精排，Metadata Filter |
| SQLite（自动建表） | PostgreSQL |
| 本地脚本生成的示例数据 | 线上数据源（趋势平台、供应商、商标库、认证机构） |
| 内存进度 | Redis + SSE 流式推送 |
| 确定性「取证清单」驱动工具 | ReAct 循环按取证清单动态选择数据源 |

---

## License

MIT
