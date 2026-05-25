# 🚀 TrendFlow AI

AI-powered trend discovery and social content automation pipeline built with Python, Gemini AI, Reddit RSS, Google Trends, SQLite, and modular CLI orchestration.

TrendFlow AI automatically:
- discovers live trending topics,
- analyzes engagement potential using Gemini structured outputs,
- generates platform-specific content drafts,
- and orchestrates the entire workflow through a resilient CLI pipeline.

---

# ✨ Features

## 🔍 Live Trend Discovery
Fetches real-world trending topics from:
- Google Trends RSS
- Reddit RSS feeds

## 🧠 AI Trend Analysis
Uses Gemini 2.5 Flash to:
- score engagement potential,
- detect sentiment,
- identify target niche,
- suggest content angles.

## ✍️ AI Content Generation
Generates:
- LinkedIn posts
- Medium articles
- X/Twitter summaries

## ⚙️ CLI Workflow Orchestration
Production-style orchestration commands:
- `health-check`
- `fetch-trends`
- `analyze-trends`
- `generate-content`
- `run-all`

## 📊 Structured Logging
- JSON execution logs
- token usage tracking
- latency monitoring
- audit-friendly outputs

## 🛡️ Resilient Engineering
- Exponential backoff retry logic
- Gemini API quota-aware recovery
- Safe rate-limiting delays
- Duplicate trend prevention

---

# 🏗️ Architecture

```text
Google Trends RSS + Reddit RSS
                ↓
         Fetcher Engine
                ↓
            SQLite DB
                ↓
        Gemini Trend Analyzer
                ↓
      Platform Content Writers
        ↙        ↓         ↘
   LinkedIn   Medium      X/Twitter
                ↓
         File Exports + Logs
                ↓
          CLI Orchestrator
```

---

# 🧰 Tech Stack

| Category | Technologies |
|---|---|
| Language | Python 3.11 |
| AI | Gemini 2.5 Flash |
| Database | SQLite |
| APIs | Google AI Studio |
| Parsing | BeautifulSoup, lxml |
| CLI | argparse |
| Logging | JSON structured logs |
| Sources | Reddit RSS, Google Trends RSS |

---

# 📁 Project Structure

```text
trendflow-ai/
│
├── backend/
│   ├── ai/
│   ├── analyzers/
│   ├── db/
│   ├── fetchers/
│   ├── generators/
│   ├── utils/
│   └── main.py
│
├── prompts/
│
├── logs/
├── outputs/
│
├── requirements.txt
└── README.md
```

---

# ⚡ Installation

## 1. Clone Repository

```bash
git clone https://github.com/karthikota/trendflow-ai.git
cd trendflow-ai
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create `.env`

```env
GEMINI_API_KEY=your_google_ai_studio_key
```

Get your API key from:

https://aistudio.google.com/app/apikey

---

# 🚀 CLI Usage

## Health Check

```bash
python backend/main.py health-check
```

---

## Fetch Trends

```bash
python backend/main.py fetch-trends
```

---

## Analyze Trends

```bash
python backend/main.py analyze-trends --limit 1
```

---

## Generate Content

```bash
python backend/main.py generate-content --limit 1
```

---

## Full Pipeline

```bash
python backend/main.py run-all --limit 1
```

---

# 🧪 Verification Results

Successfully verified:
- live RSS ingestion,
- Gemini structured JSON scoring,
- AI content generation,
- SQLite persistence,
- structured logging,
- resilient retry workflows.

### Current Verification Metrics

- 122 Raw Trends Archived
- 12 Trend Analyses Generated
- 10 Social Content Drafts Generated

---

# 📦 Generated Outputs

TrendFlow AI exports:
- LinkedIn drafts
- Medium markdown articles
- X/Twitter summaries
- structured JSON logs

---

# 🛡️ Engineering Highlights

## Resilient Retry Logic
Handles:
- API overloads
- temporary failures
- quota spikes

using:
- exponential backoff
- intelligent retry spacing

## Quota-Aware Design
Implements:
- safe request spacing,
- rolling quota recovery,
- configurable batch limits.

## Modular Architecture
Each subsystem is independently extensible:
- fetchers
- analyzers
- generators
- orchestration layer

---

# 🔮 Future Improvements

- FastAPI REST endpoints
- n8n integration
- scheduled automation
- auto-posting workflows
- dashboard visualization
- analytics monitoring
- Docker deployment
- multi-model AI support

---

# 👨‍💻 Author

### K. Sriram Karthikeya

- GitHub: https://github.com/karthikota
- LinkedIn: https://www.linkedin.com/in/sriram-karthikeya/

---

# ⭐ Project Vision

TrendFlow AI was built as an exploration into:
- AI-assisted backend engineering,
- workflow orchestration,
- automation systems,
- resilient content pipelines,
- and production-style software architecture.

---
=======
# 🚀 TrendFlow AI

AI-powered trend discovery and social content automation pipeline built with Python, Gemini AI, Reddit RSS, Google Trends, SQLite, and modular CLI orchestration.

TrendFlow AI automatically:
- discovers live trending topics,
- analyzes engagement potential using Gemini structured outputs,
- generates platform-specific content drafts,
- and orchestrates the entire workflow through a resilient CLI pipeline.

---

# ✨ Features

## 🔍 Live Trend Discovery
Fetches real-world trending topics from:
- Google Trends RSS
- Reddit RSS feeds

## 🧠 AI Trend Analysis
Uses Gemini 2.5 Flash to:
- score engagement potential,
- detect sentiment,
- identify target niche,
- suggest content angles.

## ✍️ AI Content Generation
Generates:
- LinkedIn posts
- Medium articles
- X/Twitter summaries

## ⚙️ CLI Workflow Orchestration
Production-style orchestration commands:
- `health-check`
- `fetch-trends`
- `analyze-trends`
- `generate-content`
- `run-all`

## 📊 Structured Logging
- JSON execution logs
- token usage tracking
- latency monitoring
- audit-friendly outputs

## 🛡️ Resilient Engineering
- Exponential backoff retry logic
- Gemini API quota-aware recovery
- Safe rate-limiting delays
- Duplicate trend prevention

---

# 🏗️ Architecture

```text
Google Trends RSS + Reddit RSS
                ↓
         Fetcher Engine
                ↓
            SQLite DB
                ↓
        Gemini Trend Analyzer
                ↓
      Platform Content Writers
        ↙        ↓         ↘
   LinkedIn   Medium      X/Twitter
                ↓
         File Exports + Logs
                ↓
          CLI Orchestrator
```

---

# 🧰 Tech Stack

| Category | Technologies |
|---|---|
| Language | Python 3.11 |
| AI | Gemini 2.5 Flash |
| Database | SQLite |
| APIs | Google AI Studio |
| Parsing | BeautifulSoup, lxml |
| CLI | argparse |
| Logging | JSON structured logs |
| Sources | Reddit RSS, Google Trends RSS |

---

# 📁 Project Structure

```text
trendflow-ai/
│
├── backend/
│   ├── ai/
│   ├── analyzers/
│   ├── db/
│   ├── fetchers/
│   ├── generators/
│   ├── utils/
│   └── main.py
│
├── prompts/
│
├── logs/
├── outputs/
│
├── requirements.txt
└── README.md
```

---

# ⚡ Installation

## 1. Clone Repository

```bash
git clone https://github.com/karthikota/trendflow-ai.git
cd trendflow-ai
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create `.env`

```env
GEMINI_API_KEY=your_google_ai_studio_key
```

Get your API key from:

https://aistudio.google.com/app/apikey

---

# 🚀 CLI Usage

## Health Check

```bash
python backend/main.py health-check
```

---

## Fetch Trends

```bash
python backend/main.py fetch-trends
```

---

## Analyze Trends

```bash
python backend/main.py analyze-trends --limit 1
```

---

## Generate Content

```bash
python backend/main.py generate-content --limit 1
```

---

## Full Pipeline

```bash
python backend/main.py run-all --limit 1
```

---

# 🧪 Verification Results

Successfully verified:
- live RSS ingestion,
- Gemini structured JSON scoring,
- AI content generation,
- SQLite persistence,
- structured logging,
- resilient retry workflows.

### Current Verification Metrics

- 122 Raw Trends Archived
- 12 Trend Analyses Generated
- 10 Social Content Drafts Generated

---

# 📦 Generated Outputs

TrendFlow AI exports:
- LinkedIn drafts
- Medium markdown articles
- X/Twitter summaries
- structured JSON logs

---

# 🛡️ Engineering Highlights

## Resilient Retry Logic
Handles:
- API overloads
- temporary failures
- quota spikes

using:
- exponential backoff
- intelligent retry spacing

## Quota-Aware Design
Implements:
- safe request spacing,
- rolling quota recovery,
- configurable batch limits.

## Modular Architecture
Each subsystem is independently extensible:
- fetchers
- analyzers
- generators
- orchestration layer

---

# 🔮 Future Improvements

- FastAPI REST endpoints
- n8n integration
- scheduled automation
- auto-posting workflows
- dashboard visualization
- analytics monitoring
- Docker deployment
- multi-model AI support

---

# 👨‍💻 Author

### K. Sriram Karthikeya

- GitHub: https://github.com/karthikota
- LinkedIn: https://www.linkedin.com/in/sriram-karthikeya/

---

# ⭐ Project Vision

TrendFlow AI was built as an exploration into:
- AI-assisted backend engineering,
- workflow orchestration,
- automation systems,
- resilient content pipelines,
- and production-style software architecture.

---
