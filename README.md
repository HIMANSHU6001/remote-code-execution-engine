# 🚀 CodeSpace
A secure, scalable online judge platform for running untrusted code in isolated environments.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Sandboxed-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Celery](https://img.shields.io/badge/Celery-Async-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-DB-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Next.js](https://img.shields.io/badge/Next.js-Frontend-000000?logo=next.js&logoColor=white)](https://nextjs.org/)

---

## 📖 Overview

CodeSpace is a production-ready online judge and code execution platform. Users submit code that runs securely in isolated Docker containers, with real-time feedback and support for multiple programming languages.

**Tech Stack:** FastAPI (API) → Celery (Task Queue) → Docker (Sandbox) + PostgreSQL (Database) + Next.js (Frontend)

### Key Features

- **🔒 Secure Sandboxing** — Rootless Docker containers with seccomp restrictions and network isolation
- **⚡ Asynchronous Execution** — Non-blocking task queue powered by Celery and Redis
- **🛰️ Real-Time Results** — WebSocket integration for instant submission feedback
- **🌍 Multi-Language Support** — Python, C++, Java, Node.js (easily extensible)
- **🛡️ Rate Limiting** — Built-in protection against abuse
- **📦 Scalable Architecture** — Horizontal scaling with multiple workers

---

## 🎬 Demo Videos

### Successful Submission
<video src="https://github.com/user-attachments/assets/a2b43e1f-7116-49c4-bc0d-bc359b25a087" controls width="640"></video>

### Error Cases
<video src="https://github.com/user-attachments/assets/6de22223-7c35-4cb8-9082-ae2a0e089fc1" controls width="640"></video>

### AI Feature
<video src="https://github.com/user-attachments/assets/6a45c8fd-eefd-4436-bc31-94ffe28f8304" controls width="640"></video>

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.10+
- **Node.js** 20+
- **Docker** 24.x+
- **Docker Compose** (included with Docker Desktop)

### Setup & Run

1. **Clone & Setup Backend**
```bash
   uv venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
```

2. **Setup Frontend**
```bash
   cd frontend
   npm install
```

3. **Build Sandbox Images**
```bash
   bash scripts/build_images.sh
```

4. **Seed Database** (Optional)
```bash
   python scripts/seed_db.py
```

5. **Start Services**
```bash
   docker-compose up --build
```

   The API will be available at `http://localhost:8000`, Frontend at `http://localhost:3000`

---

## 📚 Documentation

- **[Technical Requirements Document](docs/TECHNICAL_REQUIREMENTS.md)** — System design, architecture, deployment
- **[Database Schema (ERD)](docs/ERD.svg)** — Visual entity-relationship diagram
- **[CodeSpace System Design](docs/CodeSpace%20System%20Design.png)** — High-level architecture diagram

---

## ⚖️ License

MIT License — see [LICENSE](LICENSE) for details.