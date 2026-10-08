# Security Architecture & Threat Model

This document outlines the defensive controls, authentication mechanisms, and network security policies implemented across Song Chord Analyzer.

---

## 1. Defensive Controls Summary

| Threat / Risk | Defense Mechanism | Implementation Status | Enforcement Point |
|---|---|:---:|---|
| **Unauthorized Remote Access** | Pre-shared API Key (`X-API-Key`) | **✓ Implemented** | `backend/main.py` middleware |
| **Cross-Origin Hijacking** | Strict CORS Origin Whitelisting | **✓ Implemented** | `backend/main.py` CORSMiddleware |
| **Disk Exhaustion (Denial of Service)** | 100 MB Upload Cap & Queue Limit (2) | **✓ Implemented** | `backend/api/routes.py` |
| **Path Traversal Attacks** | UUID Directory Isolation | **✓ Implemented** | `backend/api/routes.py` |
| **Eavesdropping on Cellular Data** | End-to-End TLS (HTTPS) | **✓ Implemented** | Cloudflare Tunnel (`cloudflared`) |
| **Unsigned Executable Execution** | Internal No-Op Signer | **⚠ Development Only** | `electron/sign-noop.cjs` |

---

## 2. API Key Authentication (`api_key_auth_middleware`)

When exposing the backend over the public internet via Cloudflare Tunnel, unauthorized callers could theoretically trigger expensive GPU analysis jobs.

### Enforcement:
- Set environment variable: `API_AUTH_KEY=your_secret_passphrase`.
- The middleware intercepts every incoming request:
  - If `path` is `/api/health`, `/health`, or `/assets/*`, the request passes without authentication.
  - For all other endpoints (`/api/analyze`, `/api/history`, `/api/transpose`), the request must provide:
    ```http
    X-API-Key: your_secret_passphrase
    ```
  - Missing or incorrect keys receive an immediate `HTTP 401 Unauthorized`.
