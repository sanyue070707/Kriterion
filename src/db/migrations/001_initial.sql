-- Kriterion: Initial schema
-- Product candidates, screening results, evidence items, decision cards, workflow runs

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Product candidates ──
CREATE TABLE candidates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(500) NOT NULL,
    category        VARCHAR(200) NOT NULL,
    subcategory     VARCHAR(200),
    platform        VARCHAR(50) NOT NULL,  -- 'tiktok_shop' | 'shopee'
    source_country  VARCHAR(3) NOT NULL,
    target_country  VARCHAR(3) NOT NULL,
    price_usd       DECIMAL(12,2),
    currency        VARCHAR(3) DEFAULT 'USD',
    moq             INT,
    weight_kg       DECIMAL(10,3),
    status          VARCHAR(20) DEFAULT 'pending',
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Screening results ──
CREATE TABLE screening_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID REFERENCES candidates(id) ON DELETE CASCADE,
    passed          BOOLEAN NOT NULL,
    reject_reason   TEXT,
    normalized_data JSONB,
    screened_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── Market trends (for tool queries) ──
CREATE TABLE market_trends (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category        VARCHAR(200) NOT NULL,
    platform        VARCHAR(50) NOT NULL,
    country         VARCHAR(3) NOT NULL,
    period_month    DATE NOT NULL,
    search_volume   INT,
    growth_rate_pct DECIMAL(6,2),
    avg_rating      DECIMAL(3,2),
    review_count    INT,
    top_keywords    TEXT[],
    influencer_mentions INT DEFAULT 0,
    creator_sellers INT DEFAULT 0,
    avg_monthly_revenue_usd DECIMAL(14,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_trends_lookup ON market_trends(category, platform, country, period_month);

-- ── Supplier quotes (for tool queries) ──
CREATE TABLE supplier_quotes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id     VARCHAR(50) NOT NULL,
    category        VARCHAR(200) NOT NULL,
    source_country  VARCHAR(3) NOT NULL,
    unit_price_usd  DECIMAL(12,2) NOT NULL,
    moq             INT NOT NULL,
    lead_time_days  INT NOT NULL,
    freight_mode    VARCHAR(20) NOT NULL,  -- 'sea' | 'air' | 'express'
    freight_cost_per_kg DECIMAL(8,2),
    port_of_origin  VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_quotes_lookup ON supplier_quotes(category, source_country);

-- ── Compliance policies (for tool queries) ──
CREATE TABLE compliance_policies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category        VARCHAR(200) NOT NULL,
    target_country  VARCHAR(3) NOT NULL,
    rule_type       VARCHAR(50) NOT NULL,  -- 'certification' | 'prohibition' | 'duty' | 'labeling' | 'ingredient'
    description     TEXT NOT NULL,
    severity        VARCHAR(10) NOT NULL,  -- 'block' | 'warn' | 'info'
    required_certs  TEXT[],
    banned_substances TEXT[],
    import_duty_pct DECIMAL(6,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_compliance_lookup ON compliance_policies(category, target_country);

-- ── Trademark samples ──
CREATE TABLE trademarks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(300) NOT NULL,
    category        VARCHAR(200),
    country         VARCHAR(3) NOT NULL,
    status          VARCHAR(30) NOT NULL,  -- 'active' | 'pending' | 'expired'
    owner           VARCHAR(300),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_trademark_lookup ON trademarks(name, country);

-- ── Evidence items7 items# Evidence items (one row per data point) ──
CREATE TABLE evidence_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL,
    candidate_id    UUID REFERENCES candidates(id) ON DELETE CASCADE,
    agent_type      VARCHAR(50) NOT NULL,
    dimension       VARCHAR(50) NOT NULL,
    claim           TEXT NOT NULL,
    value           DECIMAL(18,4),
    unit            VARCHAR(50),
    source_tool     VARCHAR(200) NOT NULL,
    source_url      TEXT,
    fetch_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    validity_until  TIMESTAMPTZ,
    confidence      DECIMAL(3,2) NOT NULL DEFAULT 0.80,
    raw_response    JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_evidence_run ON evidence_items(run_id);
CREATE INDEX idx_evidence_candidate ON evidence_items(candidate_id);
CREATE INDEX idx_evidence_agent ON evidence_items(agent_type);

-- ── Decision cards ──
CREATE TABLE decision_cards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID UNIQUE NOT NULL,
    candidate_id    UUID REFERENCES candidates(id) ON DELETE CASCADE,
    verdict         VARCHAR(10) NOT NULL,
    scores          JSONB NOT NULL,
    overall_score   DECIMAL(4,2) NOT NULL,
    unit_economics  JSONB,
    evidence_summary JSONB,
    risk_flags      JSONB,
    watch_reasons   JSONB,
    reviewed_by     VARCHAR(50) DEFAULT 'decision_review_agent',
    decided_at      TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_decision_candidate ON decision_cards(candidate_id);
CREATE INDEX idx_decision_verdict ON decision_cards(verdict);

-- ── Workflow runs ──
CREATE TABLE workflow_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID REFERENCES candidates(id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'pending',
    current_node    VARCHAR(50),
    progress        JSONB DEFAULT '{}',
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_workflow_status ON workflow_runs(status);
