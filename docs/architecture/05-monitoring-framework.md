# Monitoring & Observability Framework
## Comprehensive System Observability

**Version**: 1.0  
**Date**: January 2026  
**Component**: Platform Reliability + Operations

---

## Table of Contents
1. [Observability Architecture](#observability-architecture)
2. [Metrics Framework](#metrics-framework)
3. [Logging Strategy](#logging-strategy)
4. [Alerting Configuration](#alerting-configuration)
5. [SLO Definitions](#slo-definitions)
6. [Debugging Workflows](#debugging-workflows)
7. [Capacity Planning](#capacity-planning)

---

## Observability Architecture

### Three Pillars Integration

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         OBSERVABILITY ARCHITECTURE                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              APPLICATION LAYER                                    │   │
│  │                                                                                   │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │
│  │   │   Agent 1   │  │   Agent 2   │  │   Agent N   │  │  Services   │            │   │
│  │   │             │  │             │  │             │  │             │            │   │
│  │   │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │            │   │
│  │   │ │OTel SDK │ │  │ │OTel SDK │ │  │ │OTel SDK │ │  │ │OTel SDK │ │            │   │
│  │   │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │            │   │
│  │   └──────┼──────┘  └──────┼──────┘  └──────┼──────┘  └──────┼──────┘            │   │
│  │          │                │                │                │                    │   │
│  └──────────┼────────────────┼────────────────┼────────────────┼────────────────────┘   │
│             │                │                │                │                        │
│             └────────────────┴────────────────┴────────────────┘                        │
│                                      │                                                   │
│                                      ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         OPENTELEMETRY COLLECTOR                                   │   │
│  │                                                                                   │   │
│  │   ┌─────────────────────────────────────────────────────────────────────────┐    │   │
│  │   │  Receivers           │  Processors          │  Exporters               │    │   │
│  │   │  ────────────────────┼─────────────────────┼────────────────────────── │    │   │
│  │   │  • OTLP (gRPC/HTTP)  │  • Batch            │  • Prometheus (metrics)   │    │   │
│  │   │  • Prometheus        │  • Memory limiter   │  • Jaeger (traces)        │    │   │
│  │   │  • Kafka             │  • Attribute        │  • Loki (logs)            │    │   │
│  │   │  • Fluentd           │  • Tail sampling    │  • ClickHouse (analytics) │    │   │
│  │   │                      │  • Resource         │  • S3 (archive)           │    │   │
│  │   └─────────────────────────────────────────────────────────────────────────┘    │   │
│  │                                                                                   │   │
│  └──────────────────────────────────┬────────────────────────────────────────────────┘   │
│                                     │                                                    │
│          ┌──────────────────────────┼──────────────────────────┐                        │
│          │                          │                          │                        │
│          ▼                          ▼                          ▼                        │
│  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐                 │
│  │     METRICS       │   │     TRACES        │   │      LOGS         │                 │
│  │   (Prometheus)    │   │    (Jaeger)       │   │     (Loki)        │                 │
│  │                   │   │                   │   │                   │                 │
│  │ • Time-series DB  │   │ • Span storage    │   │ • Log aggregation │                 │
│  │ • 15s scrape      │   │ • Dependency map  │   │ • Label indexing  │                 │
│  │ • 30 day retain   │   │ • 7 day retain    │   │ • 14 day retain   │                 │
│  └─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘                 │
│            │                       │                       │                            │
│            └───────────────────────┴───────────────────────┘                            │
│                                    │                                                    │
│                                    ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              GRAFANA                                              │   │
│  │                                                                                   │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │
│  │   │  System     │  │  Agent      │  │  Business   │  │  Custom     │            │   │
│  │   │  Health     │  │  Performance│  │  Metrics    │  │  Queries    │            │   │
│  │   │  Dashboard  │  │  Dashboard  │  │  Dashboard  │  │  Explorer   │            │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                                    │
│                                    ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           ALERTMANAGER                                            │   │
│  │                                                                                   │   │
│  │   Routes: severity → channel                                                     │   │
│  │   ┌──────────────────────────────────────────────────────────────────────────┐   │   │
│  │   │  critical → PagerDuty (immediate)                                        │   │   │
│  │   │  warning  → Slack #alerts (5 min group)                                  │   │   │
│  │   │  info     → Slack #monitoring (30 min group)                             │   │   │
│  │   └──────────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TELEMETRY DATA FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SOURCE                    COLLECTOR              STORAGE           QUERY   │
│  ──────                    ─────────              ───────           ─────   │
│                                                                              │
│  Application Metrics ─────────────────────────▶ Prometheus ────▶ Grafana   │
│  (counters, gauges,        OTel                   (TSDB)        (PromQL)   │
│   histograms)              Collector                                        │
│                                                                              │
│  Application Traces ──────────────────────────▶ Jaeger ────────▶ Jaeger UI │
│  (spans, context)          OTel                   (Cassandra)    + Grafana  │
│                            Collector                                        │
│                                                                              │
│  Application Logs ────────────────────────────▶ Loki ──────────▶ Grafana   │
│  (structured JSON)         Vector/               (Object         (LogQL)   │
│                            Fluentd               Storage)                   │
│                                                                              │
│  Infrastructure ──────────────────────────────▶ Prometheus ────▶ Grafana   │
│  (node_exporter,           Prometheus            (TSDB)        (PromQL)   │
│   kube-state-metrics)      Scrape                                          │
│                                                                              │
│  Business Events ─────────────────────────────▶ ClickHouse ───▶ Metabase/  │
│  (generations, feedback)   Kafka                 (Column        Grafana    │
│                            Connect               Store)         (SQL)      │
│                                                                              │
│  Audit Logs ──────────────────────────────────▶ S3 + Athena ──▶ AWS        │
│  (compliance, security)    Kinesis               (Parquet)      Console    │
│                            Firehose                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Metrics Framework

### Metric Categories

```yaml
# ═══════════════════════════════════════════════════════════════════════════
# RED METRICS (Request, Error, Duration) - Per Service
# ═══════════════════════════════════════════════════════════════════════════

request_metrics:
  # Request Rate
  - name: http_requests_total
    type: counter
    labels: [service, method, endpoint, status_code, tenant_id]
    description: Total HTTP requests received
    
  # Error Rate  
  - name: http_request_errors_total
    type: counter
    labels: [service, method, endpoint, error_type, tenant_id]
    description: Total HTTP request errors
    
  # Duration
  - name: http_request_duration_seconds
    type: histogram
    labels: [service, method, endpoint, tenant_id]
    buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
    description: HTTP request duration

# ═══════════════════════════════════════════════════════════════════════════
# USE METRICS (Utilization, Saturation, Errors) - Per Resource
# ═══════════════════════════════════════════════════════════════════════════

resource_metrics:
  # CPU
  - name: container_cpu_usage_seconds_total
    type: counter
    labels: [pod, container, namespace]
    
  # Memory
  - name: container_memory_working_set_bytes
    type: gauge
    labels: [pod, container, namespace]
    
  # GPU
  - name: gpu_utilization_percent
    type: gauge
    labels: [pod, gpu_id, gpu_model]
    
  - name: gpu_memory_used_bytes
    type: gauge
    labels: [pod, gpu_id, gpu_model]
    
  # Network
  - name: container_network_receive_bytes_total
    type: counter
    labels: [pod, interface, namespace]

# ═══════════════════════════════════════════════════════════════════════════
# AGENT-SPECIFIC METRICS
# ═══════════════════════════════════════════════════════════════════════════

agent_metrics:
  # Task processing
  - name: agent_tasks_received_total
    type: counter
    labels: [agent_name, task_type, tenant_id]
    
  - name: agent_tasks_completed_total
    type: counter
    labels: [agent_name, task_type, status, tenant_id]
    
  - name: agent_task_duration_seconds
    type: histogram
    labels: [agent_name, task_type]
    buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]
    
  # Queue depth
  - name: agent_queue_depth
    type: gauge
    labels: [agent_name, queue_name]
    
  # Active processing
  - name: agent_active_tasks
    type: gauge
    labels: [agent_name]

# ═══════════════════════════════════════════════════════════════════════════
# ML/GENERATION METRICS
# ═══════════════════════════════════════════════════════════════════════════

generation_metrics:
  # Inference performance
  - name: model_inference_duration_seconds
    type: histogram
    labels: [model_name, model_version, batch_size]
    buckets: [0.1, 0.5, 1, 2, 5, 10, 20, 30, 60]
    
  - name: model_tokens_generated_total
    type: counter
    labels: [model_name, model_version]
    
  # Quality metrics
  - name: brand_consistency_score
    type: histogram
    labels: [brand_id, content_type]
    buckets: [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
    
  - name: validation_pass_rate
    type: gauge
    labels: [brand_id, validator_type]
    
  # Refinement
  - name: refinement_iterations_total
    type: counter
    labels: [brand_id, refinement_reason]

# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS METRICS
# ═══════════════════════════════════════════════════════════════════════════

business_metrics:
  # Content lifecycle
  - name: content_generated_total
    type: counter
    labels: [tenant_id, brand_id, content_type]
    
  - name: content_approved_total
    type: counter
    labels: [tenant_id, brand_id, content_type, auto_approved]
    
  - name: content_rejected_total
    type: counter
    labels: [tenant_id, brand_id, content_type, rejection_reason]
    
  # Time metrics
  - name: time_to_first_draft_seconds
    type: histogram
    labels: [brand_id, content_type]
    buckets: [5, 10, 20, 30, 45, 60, 90, 120, 180]
    
  - name: time_to_approval_seconds
    type: histogram
    labels: [brand_id, content_type]
    buckets: [60, 300, 600, 1800, 3600, 7200, 14400]
    
  # Cost
  - name: generation_cost_usd
    type: counter
    labels: [tenant_id, brand_id, cost_category]
    
  # Feedback
  - name: feedback_received_total
    type: counter
    labels: [tenant_id, brand_id, feedback_type, feedback_sentiment]

# ═══════════════════════════════════════════════════════════════════════════
# GRAPH METRICS
# ═══════════════════════════════════════════════════════════════════════════

graph_metrics:
  - name: graph_query_duration_seconds
    type: histogram
    labels: [query_type, tenant_id]
    buckets: [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1]
    
  - name: graph_nodes_traversed
    type: histogram
    labels: [query_type]
    buckets: [1, 5, 10, 25, 50, 100, 250, 500]
    
  - name: graph_cache_hit_rate
    type: gauge
    labels: [cache_type, tenant_id]
    
  - name: graph_mutations_total
    type: counter
    labels: [mutation_type, source, tenant_id]
```

### Prometheus Recording Rules

```yaml
# Recording rules for common queries (pre-computed for efficiency)

groups:
  - name: agent_performance
    interval: 30s
    rules:
      # Request rate per agent (5m window)
      - record: agent:request_rate:5m
        expr: sum(rate(agent_tasks_completed_total[5m])) by (agent_name)
        
      # Error rate per agent
      - record: agent:error_rate:5m
        expr: |
          sum(rate(agent_tasks_completed_total{status="error"}[5m])) by (agent_name)
          /
          sum(rate(agent_tasks_completed_total[5m])) by (agent_name)
          
      # P95 latency per agent
      - record: agent:latency_p95:5m
        expr: |
          histogram_quantile(0.95, 
            sum(rate(agent_task_duration_seconds_bucket[5m])) by (agent_name, le)
          )

  - name: generation_quality
    interval: 1m
    rules:
      # Average brand score per brand (1h window)
      - record: brand:consistency_score:1h_avg
        expr: |
          avg(
            histogram_quantile(0.5, 
              sum(rate(brand_consistency_score_bucket[1h])) by (brand_id, le)
            )
          ) by (brand_id)
          
      # Approval rate per brand
      - record: brand:approval_rate:1h
        expr: |
          sum(rate(content_approved_total[1h])) by (brand_id)
          /
          sum(rate(content_generated_total[1h])) by (brand_id)

  - name: cost_tracking
    interval: 5m
    rules:
      # Cost per generation (rolling 24h)
      - record: tenant:cost_per_generation:24h
        expr: |
          sum(increase(generation_cost_usd[24h])) by (tenant_id)
          /
          sum(increase(content_generated_total[24h])) by (tenant_id)
          
      # Daily cost by category
      - record: tenant:daily_cost:by_category
        expr: sum(increase(generation_cost_usd[24h])) by (tenant_id, cost_category)
```

---

## Logging Strategy

### Structured Log Format

```json
{
  "timestamp": "2026-01-19T10:30:45.123Z",
  "level": "INFO",
  "service": "image-generation-agent",
  "version": "1.0.5",
  
  "trace_id": "abc123def456789",
  "span_id": "span789xyz",
  "parent_span_id": "span456uvw",
  
  "tenant_id": "tenant_001",
  "brand_id": "brand_042",
  "request_id": "req_xyz789",
  "workflow_id": "wf_abc123",
  
  "message": "Image generation completed",
  "event": "generation.completed",
  
  "context": {
    "model": "sdxl-v1.0",
    "lora_adapter": "brand_042_v3",
    "inference_steps": 30,
    "resolution": "1024x1024"
  },
  
  "metrics": {
    "duration_ms": 18500,
    "gpu_memory_peak_gb": 28.5,
    "tokens_generated": 4096
  },
  
  "outcome": {
    "status": "success",
    "image_uri": "s3://assets/gen_xyz789.png",
    "brand_score": 0.94
  }
}
```

### Log Levels & Guidelines

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LOG LEVEL GUIDELINES                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LEVEL     │ USE CASE                          │ RETENTION │ SAMPLING      │
│  ──────────┼───────────────────────────────────┼───────────┼──────────────│
│                                                                              │
│  ERROR     │ Unrecoverable failures            │ 90 days   │ 100%         │
│            │ • Exceptions with stack traces    │           │              │
│            │ • Failed generations              │           │              │
│            │ • Data corruption detected        │           │              │
│            │                                   │           │              │
│  WARN      │ Recoverable issues                │ 30 days   │ 100%         │
│            │ • Retry attempts                  │           │              │
│            │ • Validation failures (before fix)│           │              │
│            │ • Resource pressure (>80%)        │           │              │
│            │ • Circuit breaker state changes   │           │              │
│            │                                   │           │              │
│  INFO      │ Normal operations                 │ 14 days   │ 100%         │
│            │ • Request received/completed      │           │              │
│            │ • Workflow state transitions      │           │              │
│            │ • Configuration changes           │           │              │
│            │ • Cache hit/miss                  │           │              │
│            │                                   │           │              │
│  DEBUG     │ Detailed diagnostics              │ 7 days    │ 10%          │
│            │ • Function entry/exit             │           │ (or on-demand│
│            │ • Intermediate computation        │           │  for issues) │
│            │ • Full request/response bodies    │           │              │
│            │ • Algorithm step details          │           │              │
│            │                                   │           │              │
│  TRACE     │ Deep debugging                    │ 1 day     │ 1%           │
│            │ • Every method call               │           │ (production) │
│            │ • Variable state at each step     │           │ 100% (debug) │
│            │ • Network packet details          │           │              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Log Aggregation Queries (LogQL)

```logql
# Find all errors for a specific generation request
{service="image-generation-agent"} 
  | json 
  | request_id="req_xyz789" 
  | level="ERROR"

# Trace a complete workflow
{workflow_id="wf_abc123"} 
  | json 
  | line_format "{{.timestamp}} [{{.service}}] {{.message}}"

# Find slow generations (>30s)
{service="image-generation-agent"} 
  | json 
  | metrics_duration_ms > 30000
  | line_format "{{.request_id}}: {{.metrics_duration_ms}}ms - {{.outcome_status}}"

# Count errors by type in last hour
sum by (error_type) (
  count_over_time(
    {service=~".*-agent"} 
    | json 
    | level="ERROR" 
    [1h]
  )
)

# Find brand score outliers (< 0.7)
{service="validation-agent"} 
  | json 
  | outcome_brand_score < 0.7
  | line_format "Brand: {{.brand_id}} Score: {{.outcome_brand_score}} Request: {{.request_id}}"
```

---

## Alerting Configuration

### Alert Definitions

```yaml
# ═══════════════════════════════════════════════════════════════════════════
# CRITICAL ALERTS (Page immediately)
# ═══════════════════════════════════════════════════════════════════════════

groups:
  - name: critical_alerts
    rules:
      # Service completely down
      - alert: ServiceDown
        expr: up{job=~".*-agent"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.job }} is down"
          description: "Service {{ $labels.job }} has been unreachable for 2 minutes"
          runbook: "https://runbooks.internal/service-down"
          
      # Error rate spike
      - alert: HighErrorRate
        expr: agent:error_rate:5m > 0.10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.agent_name }}"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 10%)"
          runbook: "https://runbooks.internal/high-error-rate"
          
      # Generation pipeline blocked
      - alert: GenerationQueueBlocked
        expr: agent_queue_depth{agent_name="image-generation-agent"} > 200
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Image generation queue severely backed up"
          description: "Queue depth: {{ $value }} items (>200 for 10min)"
          runbook: "https://runbooks.internal/queue-blocked"
          
      # Database connection failure
      - alert: DatabaseConnectionFailure
        expr: neo4j_connections_available == 0 OR pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection lost"
          description: "Cannot connect to {{ $labels.db_name }}"
          runbook: "https://runbooks.internal/db-connection"
          
      # GPU cluster failure
      - alert: GPUClusterDegraded
        expr: count(gpu_utilization_percent) < 4
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "GPU cluster capacity degraded"
          description: "Only {{ $value }} GPUs available (minimum: 4)"
          runbook: "https://runbooks.internal/gpu-cluster"

# ═══════════════════════════════════════════════════════════════════════════
# WARNING ALERTS (Slack notification)
# ═══════════════════════════════════════════════════════════════════════════

  - name: warning_alerts
    rules:
      # Elevated latency
      - alert: ElevatedLatency
        expr: agent:latency_p95:5m > 30
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Elevated latency on {{ $labels.agent_name }}"
          description: "P95 latency is {{ $value | humanizeDuration }} (threshold: 30s)"
          
      # Moderate queue buildup
      - alert: QueueBuildup
        expr: agent_queue_depth > 50
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Queue building up on {{ $labels.agent_name }}"
          description: "Queue depth: {{ $value }} items"
          
      # Brand score degradation
      - alert: BrandScoreDegraded
        expr: brand:consistency_score:1h_avg < 0.85
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Brand consistency degraded for {{ $labels.brand_id }}"
          description: "Average brand score: {{ $value | humanizePercentage }}"
          
      # High memory usage
      - alert: HighMemoryUsage
        expr: |
          container_memory_working_set_bytes 
          / container_spec_memory_limit_bytes > 0.85
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage in {{ $labels.pod }}"
          description: "Memory usage: {{ $value | humanizePercentage }}"
          
      # Graph query slowdown
      - alert: GraphQuerySlow
        expr: |
          histogram_quantile(0.95, 
            sum(rate(graph_query_duration_seconds_bucket[5m])) by (le)
          ) > 0.2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Graph queries are slow"
          description: "P95 query latency: {{ $value | humanizeDuration }}"
          
      # LLM API rate limiting
      - alert: LLMRateLimited
        expr: increase(llm_api_rate_limited_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM API rate limiting detected"
          description: "{{ $value }} rate-limited requests in last 5 minutes"
          
      # Cost anomaly
      - alert: CostAnomaly
        expr: |
          tenant:cost_per_generation:24h > 
          1.5 * avg_over_time(tenant:cost_per_generation:24h[7d])
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Cost anomaly for tenant {{ $labels.tenant_id }}"
          description: "Current cost/gen: ${{ $value | humanize }} (50% above 7d avg)"

# ═══════════════════════════════════════════════════════════════════════════
# INFO ALERTS (Daily digest)
# ═══════════════════════════════════════════════════════════════════════════

  - name: info_alerts
    rules:
      # Low approval rate trend
      - alert: LowApprovalRateTrend
        expr: brand:approval_rate:1h < 0.70
        for: 4h
        labels:
          severity: info
        annotations:
          summary: "Low approval rate trend for {{ $labels.brand_id }}"
          description: "Approval rate: {{ $value | humanizePercentage }} over 4h"
          
      # Certificate expiring
      - alert: CertificateExpiringSoon
        expr: (probe_ssl_earliest_cert_expiry - time()) / 86400 < 30
        labels:
          severity: info
        annotations:
          summary: "SSL certificate expiring soon"
          description: "Certificate for {{ $labels.target }} expires in {{ $value }} days"
```

### Alertmanager Routing

```yaml
# alertmanager.yml

global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/XXX/YYY/ZZZ'
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'

route:
  receiver: 'default-slack'
  group_by: ['alertname', 'tenant_id']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  
  routes:
    # Critical → PagerDuty (immediate)
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      group_wait: 10s
      group_interval: 1m
      repeat_interval: 15m
      
    # Warning → Slack #alerts
    - match:
        severity: warning
      receiver: 'slack-warnings'
      group_wait: 1m
      group_interval: 5m
      repeat_interval: 1h
      
    # Info → Slack #monitoring (batched)
    - match:
        severity: info
      receiver: 'slack-info'
      group_wait: 30m
      group_interval: 1h
      repeat_interval: 24h

receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '<pagerduty-integration-key>'
        severity: critical
        details:
          firing: '{{ template "pagerduty.default.instances" .Alerts.Firing }}'
          
  - name: 'slack-warnings'
    slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: '{{ template "slack.default.title" . }}'
        text: '{{ template "slack.default.text" . }}'
        
  - name: 'slack-info'
    slack_configs:
      - channel: '#monitoring'
        send_resolved: false
        title: 'Daily Alert Summary'
        text: '{{ template "slack.default.text" . }}'
        
  - name: 'default-slack'
    slack_configs:
      - channel: '#alerts'
        send_resolved: true

inhibit_rules:
  # Don't alert on warning if critical is firing for same service
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'service']
```

---

## SLO Definitions

### Service Level Objectives

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SERVICE LEVEL OBJECTIVES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  SLO 1: GENERATION AVAILABILITY                                     │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  Objective: 99.5% of generation requests complete successfully      │     │
│  │                                                                      │     │
│  │  SLI: Successful generations / Total generation requests            │     │
│  │                                                                      │     │
│  │  PromQL:                                                            │     │
│  │  sum(rate(content_generated_total{status="success"}[30d]))          │     │
│  │  /                                                                   │     │
│  │  sum(rate(content_generated_total[30d]))                            │     │
│  │                                                                      │     │
│  │  Error Budget: 0.5% = 432 minutes/month of failures                 │     │
│  │                                                                      │     │
│  │  Current Status: ████████████████████░ 99.7% (on track)            │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  SLO 2: GENERATION LATENCY                                          │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  Objective: 95% of generations complete within 30 seconds           │     │
│  │                                                                      │     │
│  │  SLI: Generations < 30s / Total generations                         │     │
│  │                                                                      │     │
│  │  PromQL:                                                            │     │
│  │  sum(rate(http_request_duration_seconds_bucket{                     │     │
│  │    endpoint="/generate", le="30"                                     │     │
│  │  }[30d]))                                                            │     │
│  │  /                                                                   │     │
│  │  sum(rate(http_request_duration_seconds_count{                      │     │
│  │    endpoint="/generate"                                              │     │
│  │  }[30d]))                                                            │     │
│  │                                                                      │     │
│  │  Error Budget: 5% = 36 hours/month of slow generations              │     │
│  │                                                                      │     │
│  │  Current Status: █████████████████░░░ 94.2% (at risk)              │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  SLO 3: BRAND CONSISTENCY                                           │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  Objective: 90% of generations achieve brand score >= 0.90         │     │
│  │                                                                      │     │
│  │  SLI: Generations with score >= 0.90 / Total generations           │     │
│  │                                                                      │     │
│  │  PromQL:                                                            │     │
│  │  sum(rate(brand_consistency_score_bucket{le="0.90"}[30d]))         │     │
│  │  /                                                                   │     │
│  │  sum(rate(brand_consistency_score_count[30d]))                      │     │
│  │                                                                      │     │
│  │  Error Budget: 10% = 72 hours/month of low-quality generations     │     │
│  │                                                                      │     │
│  │  Current Status: █████████████████████ 93.5% (exceeding)           │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  SLO 4: GRAPH QUERY PERFORMANCE                                     │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  Objective: 99% of graph queries complete within 100ms              │     │
│  │                                                                      │     │
│  │  SLI: Graph queries < 100ms / Total graph queries                  │     │
│  │                                                                      │     │
│  │  PromQL:                                                            │     │
│  │  sum(rate(graph_query_duration_seconds_bucket{le="0.1"}[30d]))     │     │
│  │  /                                                                   │     │
│  │  sum(rate(graph_query_duration_seconds_count[30d]))                 │     │
│  │                                                                      │     │
│  │  Error Budget: 1% = 7.2 hours/month of slow queries                │     │
│  │                                                                      │     │
│  │  Current Status: █████████████████████ 99.3% (on track)            │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  SLO 5: DASHBOARD RESPONSIVENESS                                    │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  Objective: 99.9% of dashboard actions complete within 2 seconds   │     │
│  │                                                                      │     │
│  │  SLI: Dashboard actions < 2s / Total dashboard actions             │     │
│  │                                                                      │     │
│  │  Error Budget: 0.1% = 43 minutes/month of slow UI                  │     │
│  │                                                                      │     │
│  │  Current Status: █████████████████████ 99.95% (exceeding)          │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Error Budget Policy

```yaml
error_budget_policy:
  # When error budget is healthy (>50% remaining)
  healthy:
    actions:
      - Continue feature development at normal pace
      - Maintain standard deployment frequency (daily)
      - Regular on-call rotation
    
  # When error budget is concerning (25-50% remaining)
  concerning:
    threshold: 0.50
    actions:
      - Prioritize reliability work (20% of sprint)
      - Reduce deployment frequency to 3x/week
      - Increase monitoring coverage
      - Review recent changes for impact
    
  # When error budget is low (10-25% remaining)
  low:
    threshold: 0.25
    actions:
      - Pause non-critical feature work
      - Deploy only critical fixes
      - Conduct incident review meeting
      - Implement additional safeguards
    
  # When error budget is exhausted (<10% remaining)
  exhausted:
    threshold: 0.10
    actions:
      - Freeze all non-emergency deploys
      - All hands on reliability
      - Executive escalation
      - Postmortem required for any outage
```

---

## Debugging Workflows

### Common Issue Investigation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEBUGGING WORKFLOW: SLOW GENERATION                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SYMPTOM: User reports generation taking >60 seconds                        │
│                                                                              │
│  STEP 1: Identify the slow request                                          │
│  ────────────────────────────────────────────────────────────────────────   │
│  # Find request in logs                                                      │
│  {service=~".*-agent"} | json | request_id="<user_provided_id>"             │
│                                                                              │
│  # Or find recent slow requests                                              │
│  {service="content-strategy-agent"}                                          │
│    | json                                                                    │
│    | metrics_duration_ms > 60000                                            │
│    | line_format "{{.request_id}}: {{.metrics_duration_ms}}ms"              │
│                                                                              │
│  STEP 2: Get the full trace                                                 │
│  ────────────────────────────────────────────────────────────────────────   │
│  # In Jaeger: Search by trace_id from logs                                  │
│  # Or: Search by tag request_id=<id>                                        │
│                                                                              │
│  STEP 3: Identify bottleneck in trace                                       │
│  ────────────────────────────────────────────────────────────────────────   │
│  Typical breakdown for slow generation:                                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [content-strategy] 65,000ms total                                  │   │
│  │    ├─ [graph-query] 150ms ✓                                         │   │
│  │    ├─ [reasoning] 8,000ms ⚠️ (normally 4,000ms)                     │   │
│  │    ├─ [image-generation] 52,000ms ❌ (normally 18,000ms)            │   │
│  │    │    └─ [sdxl_inference] 50,000ms ← BOTTLENECK                   │   │
│  │    ├─ [text-generation] 3,000ms ✓                                   │   │
│  │    └─ [validation] 1,500ms ✓                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STEP 4: Investigate bottleneck                                             │
│  ────────────────────────────────────────────────────────────────────────   │
│  # Check GPU utilization during the time window                             │
│  gpu_utilization_percent{pod=~"image-generation.*"}                         │
│                                                                              │
│  # Check for resource contention                                            │
│  rate(container_cpu_throttled_seconds_total[5m])                           │
│                                                                              │
│  # Check queue depth at time of request                                     │
│  agent_queue_depth{agent_name="image-generation-agent"}                     │
│                                                                              │
│  STEP 5: Common root causes                                                 │
│  ────────────────────────────────────────────────────────────────────────   │
│  □ Queue backup: Queue depth was 150 → scale up agents                     │
│  □ GPU OOM: Batch size too large → reduce concurrent generations           │
│  □ LoRA cache miss: First request for brand → expected, one-time          │
│  □ Complex prompt: Many constraints → optimize reasoning                   │
│  □ Network: S3 latency spike → check AWS status                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Runbook: High Error Rate

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RUNBOOK: HIGH ERROR RATE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TRIGGER: agent:error_rate:5m > 0.10 for 5 minutes                         │
│                                                                              │
│  SEVERITY: Critical                                                          │
│                                                                              │
│  IMPACT: Users experiencing failed generations                              │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  STEP 1: TRIAGE (2 min)                                                     │
│  ────────────────────────────────────────────────────────────────────────   │
│  □ Check which agent(s) affected:                                           │
│    agent:error_rate:5m{} > 0.05                                            │
│                                                                              │
│  □ Check if specific tenant affected:                                       │
│    sum by (tenant_id) (rate(agent_tasks_completed_total{status="error"}[5m]))│
│                                                                              │
│  □ Check error types:                                                        │
│    sum by (error_type) (rate(http_request_errors_total[5m]))               │
│                                                                              │
│  STEP 2: IDENTIFY ERROR TYPE (5 min)                                        │
│  ────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│  IF error_type = "dependency_failure":                                      │
│    → Check external service status:                                         │
│      • OpenAI API: https://status.openai.com                               │
│      • Neo4j: Check graph_service_up metric                                │
│      • Redis: Check redis_up metric                                         │
│    → If external service down:                                              │
│      • Enable circuit breaker fallback                                      │
│      • Notify users of degraded service                                     │
│                                                                              │
│  IF error_type = "validation_failure":                                      │
│    → Check recent graph changes:                                            │
│      {service="feedback-learning-agent"} | json | event="graph.updated"    │
│    → If bad graph update:                                                   │
│      • Rollback to previous graph version                                  │
│      • Invalidate caches                                                    │
│                                                                              │
│  IF error_type = "resource_exhaustion":                                     │
│    → Check resource metrics:                                                │
│      container_memory_working_set_bytes / container_spec_memory_limit_bytes │
│    → If OOM:                                                                │
│      • Increase memory limits                                               │
│      • Scale horizontally                                                   │
│                                                                              │
│  IF error_type = "model_error":                                             │
│    → Check model deployment:                                                │
│      {service="triton-inference-server"} | json | level="ERROR"            │
│    → If model corrupted:                                                    │
│      • Restart Triton pods                                                  │
│      • Redeploy model artifact                                              │
│                                                                              │
│  STEP 3: MITIGATE (10 min)                                                  │
│  ────────────────────────────────────────────────────────────────────────   │
│  □ If single agent affected:                                                │
│    kubectl rollout restart deployment/<agent-name>                         │
│                                                                              │
│  □ If external dependency:                                                  │
│    kubectl patch configmap circuit-breaker-config \                        │
│      -p '{"data":{"<service>_enabled":"false"}}'                           │
│                                                                              │
│  □ If code regression:                                                      │
│    kubectl rollout undo deployment/<agent-name>                            │
│                                                                              │
│  STEP 4: VERIFY (5 min)                                                     │
│  ────────────────────────────────────────────────────────────────────────   │
│  □ Confirm error rate decreasing:                                           │
│    rate(agent_tasks_completed_total{status="error"}[1m])                   │
│                                                                              │
│  □ Verify successful generations:                                           │
│    rate(content_generated_total{status="success"}[1m])                     │
│                                                                              │
│  STEP 5: POST-INCIDENT                                                      │
│  ────────────────────────────────────────────────────────────────────────   │
│  □ Create incident report in PagerDuty                                      │
│  □ Schedule postmortem if error budget impact > 5%                         │
│  □ Update runbook with new learnings                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Capacity Planning

### Resource Forecasting

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CAPACITY PLANNING MODEL                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  CURRENT STATE (January 2026)                                       │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  Workload:                                                          │     │
│  │  • Active tenants: 50                                               │     │
│  │  • Active brands: 150                                               │     │
│  │  • Daily generations: 8,000                                         │     │
│  │  • Peak concurrent users: 400                                       │     │
│  │                                                                      │     │
│  │  Resources:                                                          │     │
│  │  • GPU nodes: 2x p4d.24xlarge (16 A100 GPUs)                       │     │
│  │  • CPU nodes: 10x m6i.4xlarge                                       │     │
│  │  • Neo4j: 3-node cluster (r6g.2xlarge)                             │     │
│  │  • PostgreSQL: db.r6g.2xlarge                                       │     │
│  │  • Redis: cache.r6g.xlarge (3-node cluster)                        │     │
│  │                                                                      │     │
│  │  Utilization:                                                        │     │
│  │  • GPU: 65% average, 85% peak                                       │     │
│  │  • CPU: 45% average, 70% peak                                       │     │
│  │  • Memory: 55% average, 75% peak                                    │     │
│  │  • Neo4j: 40% capacity                                              │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  GROWTH PROJECTIONS                                                 │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  Scenario: 25% month-over-month growth                              │     │
│  │                                                                      │     │
│  │  Month    │ Tenants │ Brands │ Daily Gen │ GPU Nodes │ CPU Nodes   │     │
│  │  ─────────┼─────────┼────────┼───────────┼───────────┼───────────  │     │
│  │  Jan 2026 │   50    │  150   │   8,000   │     2     │    10       │     │
│  │  Feb 2026 │   63    │  188   │  10,000   │     2     │    12       │     │
│  │  Mar 2026 │   78    │  234   │  12,500   │     3     │    15       │     │
│  │  Apr 2026 │   98    │  294   │  15,600   │     4     │    18       │     │
│  │  May 2026 │  122    │  366   │  19,500   │     5     │    22       │     │
│  │  Jun 2026 │  153    │  459   │  24,400   │     6     │    28       │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  SCALING TRIGGERS                                                   │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  GPU Nodes:                                                          │     │
│  │  • Scale up when: avg(gpu_utilization_percent) > 75% for 30 min    │     │
│  │  • Scale down when: avg(gpu_utilization_percent) < 40% for 2 hours │     │
│  │  • Lead time: 10 minutes (warm pool)                                │     │
│  │                                                                      │     │
│  │  CPU Nodes:                                                          │     │
│  │  • Scale up when: avg(cpu_utilization) > 70% for 10 min            │     │
│  │  • Scale down when: avg(cpu_utilization) < 30% for 30 min          │     │
│  │  • Lead time: 3 minutes (Kubernetes HPA)                            │     │
│  │                                                                      │     │
│  │  Neo4j:                                                              │     │
│  │  • Scale up when: query_latency_p95 > 150ms sustained              │     │
│  │  • Add read replica when read queries > 10K/min                     │     │
│  │  • Lead time: 30 minutes (manual)                                   │     │
│  │                                                                      │     │
│  │  Redis:                                                              │     │
│  │  • Scale up when: memory_used > 80%                                 │     │
│  │  • Add shard when eviction_rate > 0                                 │     │
│  │  • Lead time: 15 minutes (ElastiCache)                              │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  COST PROJECTION                                                    │     │
│  │  ────────────────────────────────────────────────────────────────   │     │
│  │                                                                      │     │
│  │  Monthly infrastructure cost:                                       │     │
│  │                                                                      │     │
│  │  Component          │ Jan 2026  │ Jun 2026  │ Dec 2026             │     │
│  │  ───────────────────┼───────────┼───────────┼────────────────────   │     │
│  │  GPU (p4d.24xlarge) │  $47,000  │ $141,000  │ $282,000            │     │
│  │  CPU (m6i.4xlarge)  │   $5,500  │  $15,400  │  $30,800            │     │
│  │  Neo4j (r6g.2xl)    │   $2,800  │   $5,600  │  $11,200            │     │
│  │  PostgreSQL         │   $1,200  │   $2,400  │   $4,800            │     │
│  │  Redis              │     $600  │   $1,200  │   $2,400            │     │
│  │  Kafka (MSK)        │   $1,500  │   $3,000  │   $6,000            │     │
│  │  S3 + Transfer      │   $2,000  │   $6,000  │  $15,000            │     │
│  │  Observability      │   $1,500  │   $3,000  │   $6,000            │     │
│  │  ───────────────────┼───────────┼───────────┼────────────────────   │     │
│  │  TOTAL              │  $62,100  │ $177,600  │ $358,200            │     │
│  │                                                                      │     │
│  │  Cost per generation: $0.26    │   $0.24   │   $0.22              │     │
│  │  (improves with scale due to batching efficiency)                   │     │
│  │                                                                      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Next Document

Continue to **[06-implementation-roadmap.md](./06-implementation-roadmap.md)** for the phased delivery plan and timeline.
