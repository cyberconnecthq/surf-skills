# Architecture Guide

## Project Overview

| Project | Purpose | API Type | Key Features |
|---------|---------|----------|--------------|
| **muninn** | Crypto project analysis API | REST (Gin) + Swagger | User auth, project data, trending, subscriptions |
| **argus** | Tweet monitoring & analytics | gRPC | Real-time stream processing, signal detection, mindshare |

## Multi-Mode Architecture

Both services support multiple execution modes via `exec.mode` config:

### muninn Modes

| Mode | Entry Point | Description |
|------|-------------|-------------|
| `api` | `internal/start/api.go` | REST API server (port 8080) |
| `task` | `internal/start/task.go` | Background task processor |
| `dev` | Both concurrently | Local development |

### argus Modes

| Mode | Entry Point | Description |
|------|-------------|-------------|
| `api` | `internal/start/api.go` | gRPC server + health checks |
| `task` | `internal/start/task.go` | KCL workers for Kinesis streams |
| `cron` | `internal/start/cron.go` | 15+ scheduled aggregation jobs |
| `dev` | API + Task concurrently | Local development |

**Mode Selection** (`cmd/root.go`):
```go
if conf.IsApiMode() {
    start.ApiMode(service)
} else if conf.IsTaskMode() {
    start.TaskMode(service)
} else if conf.IsCronMode() {
    start.CronMode(service)
} else if conf.IsDevMode() {
    go start.ApiMode(service)
    start.TaskMode(service)
}
```

## Read/Write Database Separation

Both services use separate database clients to distribute load:

```go
type Service struct {
    EntWriteClient *ent.Client  // postgres.writer.host - for INSERT/UPDATE/DELETE
    EntROClient    *ent.Client  // postgres.ro.host - for SELECT (10s timeout)
}
```

### Usage Rules

```go
// READ operations - always use RO client
projects, err := s.EntROClient.Project.Query().
    Where(project.IDIn(ids...)).
    All(ctx)

// WRITE operations - always use Write client
_, err := s.EntWriteClient.Project.Create().
    SetName(name).
    Save(ctx)
```

## Directory Structure

```
project/
├── cmd/                    # Cobra CLI commands
│   └── root.go            # Mode selection
├── internal/
│   ├── config/            # Configuration (Viper + Nacos)
│   │   └── values.go      # Typed config values
│   ├── middleware/        # HTTP/gRPC middleware
│   ├── repository/        # Transaction helpers
│   ├── service/           # Core business logic
│   │   ├── service.go     # Service struct init
│   │   ├── *.go           # Domain logic files
│   │   └── grpc*.go       # gRPC implementations (argus)
│   ├── start/             # Mode-specific startup
│   ├── fetcher/           # External API clients (muninn)
│   └── utils/             # Utilities (workpool, etc.)
├── ent/
│   ├── schema/            # Schema definitions (source of truth)
│   └── *                  # Generated code (don't edit)
├── model/                 # Request/response models
├── config/                # YAML config files
├── docs/                  # Generated Swagger (muninn) / arch docs
└── main.go
```

## Service Struct Pattern

Both services use a central `Service` struct holding all dependencies:

```go
type Service struct {
    Config         *config.Values
    EntWriteClient *ent.Client
    EntROClient    *ent.Client
    RedisStore     *middleware.RedisStore

    // muninn-specific
    Fetchers       map[string]Fetcher

    // argus-specific
    sqsClient      *sqs.Client
    snsClient      *sns.Client
    xaiClient      *XAIClient
}
```

## Configuration Management

### Sources (priority order)
1. Environment variables
2. YAML files (`config/local.yaml`)
3. Nacos (dynamic config)

### Key Config Sections

```yaml
exec:
  mode: dev  # api / task / cron / dev

postgres:
  host: localhost
  ro:
    host: localhost  # Read replica
  writer:
    host: localhost  # Primary
  port: 5432
  user: postgres
  password: postgres
  dbname: odin
```

### Nacos Dynamic Config (JSON)
- `kcl`: Kinesis stream configs
- `aggregation`: Cron job enable/disable flags
- `tweet_signal_monitor`: Detection thresholds
- `datadog`: Metrics configuration

## External Integrations

### muninn (22 integrations)
- **Crypto Data**: Coingecko, CryptoRank, DeFiLlama, GeckoTerminal
- **Blockchain**: GoldSky, Hyperliquid, GoPlus
- **Payments**: Stripe, RevenueCat, Daimo
- **Auth**: Firebase, Apple, Google
- **Push**: FCM

### argus (AWS-centric)
- **Kinesis**: Tweet stream, Following stream (KCL consumers)
- **DynamoDB**: Follower relationships
- **SNS/SQS**: Tweet notifications, crawl queues
- **X.AI**: Sentiment analysis

## Graceful Shutdown

muninn supports graceful shutdown with WebSocket awareness:
- 30-minute timeout for long-lived chat connections
- Health check returns 503 during shutdown (Kubernetes readiness)
