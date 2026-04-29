# GitOps-Driven CI/CD Pipeline Guide

## Smart Document Chatbot — Complete Implementation Reference

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Step 1 — Event Detection (Git Push & Pull Request)](#3-step-1--event-detection)
4. [Step 2 — Build Docker Images](#4-step-2--build-docker-images)
5. [Step 3 — Trivy Security Scanning](#5-step-3--trivy-security-scanning)
6. [Step 4 — SonarQube Code Quality Analysis](#6-step-4--sonarqube-code-quality-analysis)
7. [Step 5 — Push Vetted Images to Registry](#7-step-5--push-vetted-images-to-registry)
8. [Step 6 — Argo CD Kubernetes Synchronization](#8-step-6--argo-cd-kubernetes-synchronization)
9. [Step 7 — Rollback, Monitoring & Compliance](#9-step-7--rollback-monitoring--compliance)
10. [Repository Structure](#10-repository-structure)
11. [Operations Runbook](#11-operations-runbook)
12. [GitHub Secrets & Variables Configuration](#12-github-secrets--variables)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPER WORKFLOW                               │
│                                                                         │
│   git push / PR ──► GitHub ──► GitHub Actions (CI/CD)                  │
│                                     │                                   │
│                    ┌────────────────┼────────────────┐                  │
│                    │                │                │                  │
│                    ▼                ▼                ▼                  │
│              Build & Test    Trivy Scan       SonarQube               │
│                    │                │                │                  │
│                    └────────┬───────┘                │                  │
│                             │                        │                  │
│                    ┌────────▼────────┐               │                  │
│                    │  Quality Gate   │◄──────────────┘                  │
│                    │  (all must pass)│                                  │
│                    └────────┬────────┘                                  │
│                             │                                           │
│                    ┌────────▼────────┐                                  │
│                    │  Push Images    │                                  │
│                    │  to GHCR       │                                  │
│                    └────────┬────────┘                                  │
│                             │                                           │
│                    ┌────────▼─────────────────┐                        │
│                    │  Update K8s Manifests     │ (GitOps trigger)      │
│                    │  in Git (image tag)       │                        │
│                    └────────┬─────────────────┘                        │
│                             │                                           │
└─────────────────────────────┼───────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                                    │
│                             │                                           │
│                    ┌────────▼────────┐                                  │
│                    │    Argo CD      │ (watches Git repo)              │
│                    │  detects diff   │                                  │
│                    └────────┬────────┘                                  │
│                             │                                           │
│              ┌──────────────┼──────────────┐                           │
│              ▼              ▼              ▼                           │
│        ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│        │ Frontend │  │ Backend  │  │ Database │                      │
│        │ (Nginx)  │  │ (Spring) │  │ (PG+QD) │                      │
│        └──────────┘  └──────────┘  └──────────┘                      │
│                             │                                           │
│                    ┌────────▼────────┐                                  │
│                    │  Prometheus +   │                                  │
│                    │  Grafana + Loki │                                  │
│                    └─────────────────┘                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Principle

This pipeline follows the **GitOps** model: Git is the single source of truth for both application code _and_ infrastructure state. No human or CI system pushes directly to the cluster. Instead, CI updates a declarative manifest in Git, and Argo CD reconciles the cluster to match.

### Pipeline Stages Summary

| Stage | Trigger | Tool | File |
|-------|---------|------|------|
| 1. Event detection | `git push`, PR | GitHub Actions | `.github/workflows/ci.yml` |
| 2. Build images | CI passes | Docker Buildx | `docker/Dockerfile.*` |
| 3. Security scan | Images built | Trivy | CI workflow stage 4 |
| 4. Code quality | Code compiled | SonarQube | `*/sonar-project.properties` |
| 5. Push images | All scans pass | GHCR | CD workflow stage 1 |
| 6. K8s sync | Manifest updated | Argo CD | `k8s/argocd/*.yml` |
| 7. Verify & monitor | Post-deploy | Prometheus/Grafana | `docker/monitoring/*` |

---

## 2. Prerequisites

### Infrastructure Requirements

| Component | Minimum Version | Purpose |
|-----------|----------------|---------|
| Kubernetes cluster | 1.27+ | Runtime platform |
| kubectl | 1.27+ | Cluster CLI |
| Argo CD | 2.9+ | GitOps controller |
| Docker | 24+ | Local builds (optional) |
| GitHub account | — | Source control + CI/CD |

### External Services

| Service | Required? | Setup Guide |
|---------|-----------|-------------|
| **SonarQube** | Recommended | Self-hosted or SonarCloud |
| **Slack** | Optional | Deployment notifications |
| **cert-manager** | Production | TLS certificate automation |

### Cluster Prerequisites

```bash
# 1. Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 2. Install Argo CD CLI
# macOS:
brew install argocd
# Linux:
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/

# 3. Get initial admin password
argocd admin initial-password -n argocd

# 4. Login
argocd login <ARGOCD_SERVER> --username admin --password <PASSWORD>

# 5. Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml

# 6. Install cert-manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

---

## 3. Step 1 — Event Detection

**File: `.github/workflows/ci.yml`** (lines 8-13)

### How It Works

GitHub Actions automatically detects two event types:

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

### Event Routing Logic

| Event | Branch | What Happens |
|-------|--------|--------------|
| `push` | `main` | Full CI + CD to staging |
| `push` | `develop` | CI only (build, test, scan) |
| `pull_request` | `main` or `develop` | Full CI + SonarQube + Trivy (PR gate) |
| `tag` | `v*` | Full CI + CD to production |

### Manual Deployment

The CD workflow also supports `workflow_dispatch` for manual deployments:

```yaml
# In .github/workflows/cd.yml
on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [staging, production]
      image_tag:
        description: 'Image tag to deploy'
```

Trigger via GitHub UI: **Actions → CD Pipeline → Run workflow**.

---

## 4. Step 2 — Build Docker Images

**Files:**
- `docker/Dockerfile.backend` — Multi-stage Maven + JRE build
- `docker/Dockerfile.frontend` — Multi-stage Node.js + Nginx build

### Backend Build Strategy

```
┌──────────────────────┐     ┌──────────────────────┐
│   Stage 1: BUILD     │     │   Stage 2: RUNTIME   │
│                      │     │                      │
│ maven:3.9-temurin-17 │────►│ temurin:17-jre-alpine│
│                      │     │                      │
│ • pom.xml (cached)   │     │ • app.jar only       │
│ • mvn package        │     │ • non-root user      │
│ • ~800MB             │     │ • health check       │
│                      │     │ • ~200MB             │
└──────────────────────┘     └──────────────────────┘
```

Key features of the Dockerfile design:

1. **Dependency caching**: `pom.xml` copied separately before source code so `mvn dependency:go-offline` is cached across builds.
2. **Minimal runtime**: JRE-only Alpine image (no JDK, no build tools).
3. **Non-root execution**: `appuser` with restricted permissions.
4. **Container-aware JVM**: `-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0`.
5. **Built-in health check**: Actuator endpoint.

### Frontend Build Strategy

```
┌──────────────────────┐     ┌──────────────────────┐
│   Stage 1: BUILD     │     │   Stage 2: RUNTIME   │
│                      │     │                      │
│ node:18-alpine       │────►│ nginx:1.25-alpine    │
│                      │     │                      │
│ • npm ci             │     │ • static HTML/JS/CSS │
│ • npm run build      │     │ • reverse proxy      │
│ • ~500MB             │     │ • security headers   │
│                      │     │ • ~30MB              │
└──────────────────────┘     └──────────────────────┘
```

### CI Build Stage

In the CI workflow (`.github/workflows/ci.yml`, job `docker-build`), images are built and pushed to GHCR with commit SHA tags:

```yaml
tags: |
  ghcr.io/OWNER/smart-doc-chatbot/backend:<sha>
  ghcr.io/OWNER/smart-doc-chatbot/frontend:<sha>
```

**Build args** for the frontend allow environment-specific API URLs:

```yaml
build-args: |
  REACT_APP_API_URL=/api
  REACT_APP_WS_URL=/ws
```

---

## 5. Step 3 — Trivy Security Scanning

**File: `.github/workflows/ci.yml`** (jobs `trivy-scan-backend`, `trivy-scan-frontend`, `trivy-scan-iac`)

### Three Scan Layers

| Scan Type | What It Checks | Exit Code |
|-----------|---------------|-----------|
| **Image scan (backend)** | OS packages, Java JARs in the container | `1` (fails on CRITICAL/HIGH) |
| **Image scan (frontend)** | OS packages, npm modules in the container | `1` (fails on CRITICAL/HIGH) |
| **IaC/Config scan** | Dockerfiles, K8s manifests, Compose files | `0` (advisory only) |

### Image Scanning Flow

```
Docker Image Built
       │
       ▼
Trivy pulls image from GHCR
       │
       ▼
Scans OS packages (Alpine APK, Debian apt)
       │
       ▼
Scans application dependencies (Maven JARs, npm packages)
       │
       ▼
Generates SARIF report
       │
       ├──► Uploaded to GitHub Security tab (Code Scanning)
       │
       └──► Table output in workflow logs
```

### SARIF Integration

Trivy results are uploaded to GitHub's Security tab via SARIF format:

```yaml
- name: Upload Trivy SARIF (backend)
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-backend.sarif'
    category: 'trivy-backend'
```

This allows developers to review vulnerabilities directly in the **Security → Code scanning alerts** tab.

### Configuration Details

- **Severity threshold**: `CRITICAL,HIGH` — only these block the pipeline
- **`ignore-unfixed: true`** — skip vulnerabilities without available patches
- **IaC scanning** checks for misconfigurations in:
  - Dockerfiles (e.g., running as root, pinning versions)
  - Kubernetes manifests (e.g., missing resource limits, privileged containers)
  - Docker Compose files

### Handling Failures

If Trivy finds CRITICAL/HIGH vulnerabilities:
1. The image scan job fails (`exit-code: 1`)
2. The `ci-gate` job reports the failure
3. The PR cannot be merged (if branch protection is enabled)
4. Developers review the SARIF report in the Security tab
5. Fix: update base image, patch dependencies, or add `.trivyignore`

---

## 6. Step 4 — SonarQube Code Quality Analysis

**Files:**
- `.github/workflows/ci.yml` (jobs `sonarqube-backend`, `sonarqube-frontend`)
- `backend/sonar-project.properties`
- `frontend/sonar-project.properties`

### Setup SonarQube

#### Option A: SonarCloud (Recommended for open source)

1. Go to [sonarcloud.io](https://sonarcloud.io) and connect your GitHub org.
2. Create two projects: `smart-doc-chatbot-backend` and `smart-doc-chatbot-frontend`.
3. Copy the token and set it as `SONAR_TOKEN` secret.
4. Set `SONAR_HOST_URL` = `https://sonarcloud.io`.

#### Option B: Self-hosted SonarQube

```bash
# Run SonarQube locally or on a server
docker run -d --name sonarqube \
  -p 9000:9000 \
  -v sonarqube_data:/opt/sonarqube/data \
  sonarqube:community

# Access at http://localhost:9000 (admin/admin)
# Create projects and generate tokens
```

### Backend Analysis

The backend uses the Maven SonarQube plugin:

```bash
mvn clean verify sonar:sonar \
  -Dsonar.projectKey=smart-doc-chatbot-backend \
  -Dsonar.host.url=$SONAR_HOST_URL \
  -Dsonar.token=$SONAR_TOKEN \
  -Dsonar.qualitygate.wait=true   # Block if gate fails
```

Analysis includes:
- **Code coverage** via JaCoCo (`jacoco.xml`)
- **Bug detection** (null pointers, resource leaks)
- **Code smells** (complexity, duplication)
- **Security hotspots** (SQL injection, XSS patterns)
- **Technical debt** estimation

### Frontend Analysis

The frontend uses the `sonarqube-scan-action`:

```yaml
- uses: SonarSource/sonarqube-scan-action@v3
  with:
    projectBaseDir: frontend
    args: >
      -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info
      -Dsonar.qualitygate.wait=true
```

### Quality Gate

The default SonarQube quality gate requires:
- **Coverage** ≥ 80% on new code
- **Duplications** < 3% on new code
- **No new bugs** with severity ≥ Major
- **No new vulnerabilities**
- **No new security hotspots** (unreviewed)

If `sonar.qualitygate.wait=true` is set, the CI step blocks until the gate result is available and fails the pipeline if the gate is red.

### Adding JaCoCo to Backend

Add this to `backend/pom.xml` inside `<plugins>`:

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.11</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals><goal>report</goal></goals>
        </execution>
    </executions>
</plugin>
```

---

## 7. Step 5 — Push Vetted Images to Registry

**File: `.github/workflows/cd.yml`** (job `build-and-push`)

### Registry: GitHub Container Registry (GHCR)

Images are pushed to `ghcr.io/<owner>/smart-doc-chatbot/{backend,frontend}`.

### Tagging Strategy

| Trigger | Tag Format | Example |
|---------|-----------|---------|
| Push to `main` | `<commit-sha>` | `a1b2c3d4` |
| Version tag | `<tag-name>` | `v1.2.0` |
| Both | `latest` | `latest` |

### Authentication

GHCR uses the built-in `GITHUB_TOKEN`:

```yaml
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

No external registry credentials needed.

### Image Metadata

Docker metadata (OCI labels) is attached to every image:

```yaml
- uses: docker/metadata-action@v5
  with:
    images: ghcr.io/${{ github.repository }}/backend
    tags: |
      type=sha,prefix=
      type=ref,event=pr
      type=semver,pattern={{version}}
```

This enables traceability: every container image can be linked back to its exact source commit.

---

## 8. Step 6 — Argo CD Kubernetes Synchronization

**Files:**
- `k8s/argocd/project.yml` — Argo CD project (RBAC)
- `k8s/argocd/staging-app.yml` — Staging Application
- `k8s/argocd/production-app.yml` — Production Application
- `k8s/base/*` — Base Kubernetes manifests
- `k8s/overlays/staging/` — Staging Kustomize overlay
- `k8s/overlays/production/` — Production Kustomize overlay

### GitOps Flow

```
CD Pipeline updates kustomization.yml (newTag: <sha>)
       │
       ▼
Git commit pushed to main branch
       │
       ▼
Argo CD polls repo (every 3 min) or receives webhook
       │
       ▼
Argo CD detects diff between Git state and cluster state
       │
       ▼
Argo CD syncs:
  ├── Staging:    AUTO-SYNC (immediate)
  └── Production: MANUAL SYNC (requires approval)
       │
       ▼
Kubernetes rolling update (maxSurge: 1, maxUnavailable: 0)
       │
       ▼
Health checks pass → Deployment complete
```

### Install Argo CD Applications

```bash
# 1. Create the project
kubectl apply -f k8s/argocd/project.yml

# 2. Create the staging application
kubectl apply -f k8s/argocd/staging-app.yml

# 3. Create the production application
kubectl apply -f k8s/argocd/production-app.yml

# 4. Verify
argocd app list
```

### Staging vs Production Sync Policies

| Aspect | Staging | Production |
|--------|---------|------------|
| **Auto-sync** | Enabled | Disabled (manual) |
| **Self-heal** | Enabled | N/A |
| **Prune** | Enabled | Enabled |
| **Replicas** | 1 | 3 (backend), 2 (frontend) |
| **HPA range** | 1-3 | 2-6 |
| **Resources** | Reduced | Full allocation |

### Kustomize Overlay Structure

```
k8s/
├── base/                          # Shared manifests
│   ├── kustomization.yml
│   ├── backend-deployment.yml
│   ├── backend-service.yml
│   ├── backend-configmap.yml
│   ├── backend-secret.yml
│   ├── frontend-deployment.yml
│   ├── frontend-service.yml
│   ├── postgres-statefulset.yml
│   ├── qdrant-statefulset.yml
│   ├── ingress.yml
│   ├── hpa.yml
│   ├── network-policy.yml
│   ├── pvc.yml
│   ├── service-account.yml
│   └── namespace.yml
│
├── overlays/
│   ├── staging/
│   │   └── kustomization.yml     # Patches: 1 replica, debug logs, staging host
│   └── production/
│       ├── kustomization.yml     # Patches: 3 replicas, warn logs, prod host
│       └── pod-disruption-budget.yml
│
└── argocd/
    ├── project.yml
    ├── staging-app.yml
    └── production-app.yml
```

### How the CD Workflow Triggers Argo CD

The CD workflow does NOT deploy directly. Instead, it commits a manifest change:

```yaml
# .github/workflows/cd.yml — deploy-staging job
- name: Update staging image tags
  run: |
    cd k8s/overlays/staging
    sed -i "s|newTag: .*|newTag: ${TAG}|g" kustomization.yml

- name: Commit and push manifest changes
  run: |
    git commit -m "chore(deploy): update staging images to ${TAG}"
    git push origin main
```

Argo CD detects this commit and syncs the cluster. This is the core GitOps principle — the cluster state always matches Git.

### Setting Up Argo CD Webhook (Faster Sync)

By default, Argo CD polls Git every 3 minutes. For instant deployment:

1. In your GitHub repo: **Settings → Webhooks → Add webhook**
2. Payload URL: `https://<argocd-server>/api/webhook`
3. Content type: `application/json`
4. Secret: Set in Argo CD config
5. Events: "Just the push event"

---

## 9. Step 7 — Rollback, Monitoring & Compliance

### Rollback

**File: `.github/workflows/compliance.yml`** (jobs `rollback-staging`, `rollback-production`)

#### Automatic Rollback (Argo CD)

Argo CD maintains a revision history (`revisionHistoryLimit: 10` for staging, `15` for production). To rollback via Argo CD CLI:

```bash
# View history
argocd app history smart-doc-chatbot-staging

# Rollback to previous revision
argocd app rollback smart-doc-chatbot-staging <REVISION>

# Or rollback to previous sync
argocd app rollback smart-doc-chatbot-staging
```

#### GitOps Rollback (via workflow)

Trigger the compliance workflow with `rollback-staging` or `rollback-production`:

**Actions → Compliance & Verification → Run workflow → Select "rollback-staging"**

This workflow:
1. Finds the previous image tag from Git history
2. Reverts the `kustomization.yml` to that tag
3. Commits the revert
4. Argo CD syncs the old version back

#### Kubernetes Native Rollback

```bash
# View rollout history
kubectl rollout history deployment/backend -n smart-doc-chatbot-staging

# Rollback to previous revision
kubectl rollout undo deployment/backend -n smart-doc-chatbot-staging

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=3 -n smart-doc-chatbot-staging
```

#### Database Rollback

For database-level rollback, Flyway supports versioned migrations:

```bash
# Flyway will only run forward migrations
# To rollback: create a new migration that reverts changes
# e.g., V3__revert_v2_changes.sql
```

### Monitoring

#### Stack Overview

| Tool | Purpose | Access |
|------|---------|--------|
| **Prometheus** | Metrics collection | `http://localhost:9090` |
| **Grafana** | Dashboards | `http://localhost:3001` |
| **Loki** | Log aggregation | Via Grafana |
| **Spring Actuator** | App health/metrics | `/api/actuator/*` |

#### Key Metrics Monitored

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Service availability | `up{job="backend"}` | Down > 1 min |
| HTTP 5xx rate | `http_server_requests_seconds_count` | > 5% for 5 min |
| P95 latency | `http_server_requests_seconds_bucket` | > 5s for 5 min |
| JVM heap usage | `jvm_memory_used_bytes` | > 85% for 5 min |
| DB connection pool | `hikaricp_connections_active` | > 90% for 2 min |
| Disk space | `node_filesystem_avail_bytes` | < 10% for 5 min |

#### Grafana Dashboards

Pre-configured datasources are auto-provisioned:

```yaml
# docker/monitoring/grafana/provisioning/datasources/datasources.yml
datasources:
  - name: Prometheus    # Metrics
  - name: Loki          # Logs
```

Import recommended dashboards in Grafana:
- **Spring Boot**: Dashboard ID `12900`
- **JVM Micrometer**: Dashboard ID `4701`
- **Nginx**: Dashboard ID `12708`
- **PostgreSQL**: Dashboard ID `9628`

#### Enabling Monitoring in Kubernetes

```bash
# Using the monitoring compose overlay
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.monitoring.yml up -d

# Or in Kubernetes, install kube-prometheus-stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace
```

### Compliance Verification

**File: `.github/workflows/compliance.yml`** (job `compliance-scan`)

The compliance workflow runs:

| Check | Frequency | What It Does |
|-------|-----------|--------------|
| **Trivy full scan** | Weekly + post-deploy | Scans entire filesystem for CRITICAL/HIGH/MEDIUM vulnerabilities |
| **License audit (backend)** | Weekly | Maven dependency license check |
| **License audit (frontend)** | Weekly | NPM license-checker (blocks GPL-3.0, AGPL-3.0) |
| **K8s manifest validation** | Weekly | Validates YAML syntax + K8s schema |
| **Secret detection** | Weekly | Scans for hardcoded passwords/keys/tokens |
| **Dockerfile audit** | Weekly | Checks non-root USER, HEALTHCHECK presence |

#### Schedule

```yaml
schedule:
  - cron: '0 6 * * 1'  # Every Monday at 6:00 UTC
```

---

## 10. Repository Structure

```
Smart Document Chatbot/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    # CI: build, test, scan, analyze
│       ├── cd.yml                    # CD: push images, update manifests
│       └── compliance.yml            # Post-deploy verification, rollback
│
├── k8s/
│   ├── base/                         # Base Kubernetes manifests
│   │   ├── kustomization.yml
│   │   ├── namespace.yml
│   │   ├── service-account.yml
│   │   ├── backend-deployment.yml
│   │   ├── backend-service.yml
│   │   ├── backend-configmap.yml
│   │   ├── backend-secret.yml
│   │   ├── frontend-deployment.yml
│   │   ├── frontend-service.yml
│   │   ├── postgres-statefulset.yml
│   │   ├── qdrant-statefulset.yml
│   │   ├── ingress.yml
│   │   ├── hpa.yml
│   │   ├── network-policy.yml
│   │   └── pvc.yml
│   ├── overlays/
│   │   ├── staging/
│   │   │   └── kustomization.yml
│   │   └── production/
│   │       ├── kustomization.yml
│   │       └── pod-disruption-budget.yml
│   └── argocd/
│       ├── project.yml
│       ├── staging-app.yml
│       └── production-app.yml
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml            # Production compose
│   ├── docker-compose.dev.yml        # Dev infrastructure
│   ├── docker-compose.monitoring.yml # Monitoring stack
│   ├── nginx/
│   │   └── nginx.conf
│   ├── init-db/
│   │   └── 01-init.sql
│   └── monitoring/
│       ├── prometheus.yml
│       ├── alert-rules.yml
│       ├── promtail.yml
│       └── grafana/provisioning/
│
├── backend/
│   ├── pom.xml
│   ├── sonar-project.properties
│   └── src/
│
├── frontend/
│   ├── package.json
│   ├── sonar-project.properties
│   └── src/
│
├── scripts/
│   ├── deploy.sh
│   ├── rollback.sh
│   └── health-check.sh
│
├── .dockerignore
├── .env.example
├── .env.production
├── .env.staging
└── Makefile
```

---

## 11. Operations Runbook

### First-Time Setup

```bash
# 1. Clone the repository
git clone https://github.com/OWNER/smart-doc-chatbot.git
cd smart-doc-chatbot

# 2. Configure secrets in GitHub
#    Settings → Secrets and variables → Actions
#    See Section 12 below for full list

# 3. Replace OWNER placeholders in K8s manifests
find k8s/ -name '*.yml' -exec sed -i 's|OWNER|your-github-username|g' {} +

# 4. Replace example.com with your domain
find k8s/ -name '*.yml' -exec sed -i 's|example.com|yourdomain.com|g' {} +

# 5. Install Argo CD apps
kubectl apply -f k8s/argocd/project.yml
kubectl apply -f k8s/argocd/staging-app.yml
kubectl apply -f k8s/argocd/production-app.yml

# 6. Create actual secrets in cluster (don't use the template ones)
kubectl create secret generic backend-secrets \
  --from-literal=SPRING_DATASOURCE_USERNAME=prod_user \
  --from-literal=SPRING_DATASOURCE_PASSWORD=<strong-password> \
  --from-literal=OPENAI_API_KEY=sk-<your-key> \
  --from-literal=QDRANT_API_KEY=<your-key> \
  -n smart-doc-chatbot-production

# 7. Push to main to trigger the first deployment
git push origin main
```

### Daily Operations

```bash
# Check deployment status
argocd app get smart-doc-chatbot-staging
argocd app get smart-doc-chatbot-production

# View logs
kubectl logs -l app=backend -n smart-doc-chatbot-staging -f

# Check pod health
kubectl get pods -n smart-doc-chatbot-staging

# Manual sync (production)
argocd app sync smart-doc-chatbot-production

# Rollback
argocd app rollback smart-doc-chatbot-staging
# Or use GitHub Actions: Compliance workflow → rollback-staging
```

### Release to Production

```bash
# 1. Create a version tag
git tag v1.2.0
git push origin v1.2.0

# 2. CI runs → images tagged v1.2.0 pushed to GHCR
# 3. CD updates k8s/overlays/production/kustomization.yml
# 4. Argo CD detects change (production requires manual sync)

# 5. Review in Argo CD UI, then sync
argocd app sync smart-doc-chatbot-production

# 6. Verify
argocd app wait smart-doc-chatbot-production --health --timeout 300
```

---

## 12. GitHub Secrets & Variables

### Required Secrets

| Secret | Description | Where to Get |
|--------|-------------|-------------|
| `SONAR_TOKEN` | SonarQube/SonarCloud auth token | SonarQube → My Account → Security → Tokens |
| `SONAR_HOST_URL` | SonarQube server URL | `https://sonarcloud.io` or self-hosted URL |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook | Slack → Apps → Incoming Webhooks |

### Required Variables (per environment)

| Variable | Environment | Description |
|----------|-------------|-------------|
| `STAGING_URL` | staging | e.g., `https://staging.smartdoc.example.com` |
| `PRODUCTION_URL` | production | e.g., `https://smartdoc.example.com` |

### GitHub Token Permissions

The built-in `GITHUB_TOKEN` is used for:
- Pushing images to GHCR (`packages: write`)
- Committing manifest changes (`contents: write`)
- Uploading SARIF reports (`security-events: write`)

No additional PATs needed unless branch protection requires signed commits.

---

## Summary

This GitOps pipeline provides a complete, production-grade CI/CD system:

1. **Automated detection** of every push and PR via GitHub Actions
2. **Multi-stage Docker builds** with dependency caching and minimal runtime images
3. **Three-layer Trivy scanning** (backend image, frontend image, IaC configs) with SARIF integration
4. **SonarQube quality gates** for both Java backend and React frontend
5. **Immutable image tagging** pushed to GHCR after all checks pass
6. **GitOps deployment** via Kustomize manifest updates that Argo CD syncs to Kubernetes
7. **Rollback** via Git history revert, Argo CD revision history, or Kubernetes rollout undo
8. **Monitoring** via Prometheus + Grafana + Loki with pre-configured alert rules
9. **Weekly compliance** scans (vulnerabilities, licenses, secrets, manifest validation)
