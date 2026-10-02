# Kriterion

**多智能体选品决策系统** — 面向跨境电商卖家的自动化产品评估平台

> 从候选品提交到决策卡产出，自动完成快筛、三方取证、证据核验、交叉评审，替代人工 2~4 小时的跨平台数据整合。

---

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + SSE |
| 工作流引擎 | LangGraph |
| Agent 框架 | LangChain + ReAct |
| LLM | Qwen3-Max (可切换 Mock) |
| 向量检索 | BGE-M3 + Milvus + BM25 + bge-reranker-v2-m3 |
| 关系数据库 | PostgreSQL 16 |
| 缓存/消息 | Redis 7 |
| 可观测性 | Langfuse (可选) |

---

## 架构概览

```
候选品 → 归一化 → 快筛漏斗 → [条件边]
  ├─ 未通过 → END (rejected)
  └─ 通过 → [并行扇出]
       ├─ 趋势需求 Agent     ─┐
       ├─ 货源成本 Agent     ─┤→ 证据守门 → 决策评审 → 决策卡 → END
       └─ 合规风险 Agent     ─┘
```

### 三方取证 Agent

| Agent | 职责 | 核心工具 |
|-------|------|----------|
| 趋势需求 Agent | 市场需求、趋势动能、达人活跃度 | search_trends, get_category_growth, get_influencer_data |
| 货源成本 Agent | 供应商报价、头程费率、佣金、单位经济 | get_supplier_quotes, calculate_freight, get_platform_commission, calculate_unit_economics |
| 合规风险 Agent | 商标冲突、认证缺口、合规政策 | check_trademark, check_certifications, check_policy_compliance |

### 决策评审 Agent

- 交叉质证三方证据
- 七维打分: market_demand, competition, cost_margin, compliance_risk, supply_stability, trend_momentum, return_rate
- Go / Watch / No-Go 裁决

### 证据账本

每个业务数字绑定: 来源工具、原始地址、抓取时间、有效期、置信度。证据守门节点逐条校验并剔除无来源数字。

---

## 快速开始

### 前置要求

- Docker & Docker Compose
- Python 3.11+
- (可选) Qwen API Key — 无 Key 时自动使用 Mock LLM

### 1. 配置环境

```bash
cp .env.example .env
# 编辑 .env，按需修改配置
# 不改也能跑 — 默认使用 Mock LLM + Mock Embedding
```

### 2. 启动服务

```bash
docker compose up -d
```

等待所有服务就绪 (约 30 秒):

```bash
docker compose logs -f app  # 查看应用日志
```

### 3. 生成数据并写入

```bash
# 在容器内或本地 (需 pip install -e .)
python scripts/generate_mock_data.py
python scripts/seed_database.py
python scripts/seed_vector_store.py
```

或使用 Makefile:

```bash
make seed
```

### 4. 运行 Demo

```bash
make demo
# 或
python scripts/run_demo.py
```

### 5. API 文档

访问 http://localhost:8000/docs 查看 Swagger UI

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/candidates` | 提交候选品 |
| GET | `/api/v1/candidates` | 列出候选品 |
| GET | `/api/v1/candidates/{id}` | 获取候选品详情 |
| POST | `/api/v1/workflow/run` | 触发评估工作流 |
| GET | `/api/v1/workflow/{id}/status` | 查询工作流状态 |
| GET | `/api/v1/workflow/{id}/stream` | SSE 流式进度 |
| GET | `/api/v1/decisions` | 列出决策卡 |
| GET | `/api/v1/decisions/{id}` | 获取决策卡详情 |
| GET | `/health` | 健康检查 |

---

## 决策卡示例

```json
{
  "verdict": "go",
  "overall_score": 7.8,
  "scores": {
    "market_demand": 8.2,
    "competition": 6.5,
    "cost_margin": 8.5,
    "compliance_risk": 9.0,
    "supply_stability9": 7.0,
    "trend_momentum": 7.5,
    "return_rate": 8.0
  },
  "unit_economics": {
    "retail_price": 25.99,
    "product_cost": 8.50,
    "net_margin_pct": 18.5
  },
  "risk_flags": {},
  "watch_reasons": {}
}
```

---

## 配置说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `LLM_PROVIDER` | `mock` | `qwen` 使用 Qwen3-Max, `mock` 零 API Key 运行 |
| `QWEN_API_KEY` | 空 | Qwen API Key (LLM_PROVIDER=qwen 时必填) |
| `EMBEDDING_PROVIDER` | `mock` | `local` 使用本地 BGE-M3, `mock` 用随机向量 |
| `RERANKER_PROVIDER` | `mock` | `local` 使用本地 bge-reranker-v2-m3 |
| `LANGFUSE_ENABLED` | `false` | 启用 Langfuse 可观测性 |

---

## 项目结构

```
src/
├── main.py                 # FastAPI 入口
├── config/                 # 配置 + 平台模型
├── api/                    # API 端点 + SSE
├── db/                     # 数据- ORM + 迁移 +/ migrations/
├── rag/                    # BGE-M3 + Milvus + BM25 + Reranker
├── graph/                  # LangGraph 工作流
├── agents/                 # 四个 Agent + Prompts
├── tools/                  # MCP 业务工具
├── evidence/               # 证据账本 + 守门
├── decision/               # 打分 + 裁决 + 决策卡
├── screening/              # 归一化 + 快筛
└── llm/                    # LLM 工厂
scripts/                    # 数据生成 + 种子 + Demo
data/                       # Mock 数据 + 参考数据
tests/                      # 单元测试
docker/                     # Dockerfile + entrypoint
```

---

## License

MIT
