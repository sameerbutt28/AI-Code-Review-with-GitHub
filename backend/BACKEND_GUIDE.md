# AI Code Review Backend — FYP Guide

This document explains the **backend code structure** so you can present it to your university teachers.

---

## Project Name

**AI Code Review** — Automated GitHub Security Code Review System  
*Final Year Project (FYP)*

---

## What Does the Backend Do?

When a user submits a GitHub repository URL, the backend:

1. **Clones** the repository from GitHub
2. **Scans** source code with regex patterns (fast, no AI cost)
3. **Analyzes** code with AI (OpenAI GPT via LangChain)
4. **Generates** a PDF + Markdown security report with charts

---

## Folder Structure (Easy to Explain)

```
backend/
├── run.py                          ← Start the server (python run.py)
├── requirements.txt                ← Python packages needed
├── .env                            ← Secret keys (OpenAI API key)
│
└── app/
    ├── main.py                     ← Creates FastAPI app
    │
    ├── core/                       ← Configuration
    │   ├── config.py               ← Reads settings from .env
    │   └── prompts.py              ← AI instructions (original writing rules)
    │
    ├── models/
    │   └── schemas.py              ← Data structures (Pydantic models)
    │
    ├── api/
    │   └── routes.py               ← HTTP endpoints (what frontend calls)
    │
    ├── storage/
    │   └── review_store.py         ← Saves review status & results (in memory)
    │
    └── services/                   ← MAIN BUSINESS LOGIC (4 steps)
        ├── review_workflow.py      ← Connects all 4 steps together
        ├── step1_github_clone.py   ← Step 1: Clone repo + read files
        ├── step2_pattern_scanner.py← Step 2: Regex security scan
        ├── step3_ai_analyzer.py    ← Step 3: LangChain + GPT analysis
        ├── step4_report_generator.py← Step 4: PDF/Markdown reports
        ├── chart_renderer.py       ← Draws charts inside PDF
        └── originality_helper.py   ← Makes each report unique (anti-plagiarism)
```

---

## The 4-Step Pipeline (Present This to Teachers)

```
User clicks "Start Review"
        │
        ▼
┌───────────────────┐
│  api/routes.py    │  Receives HTTP request
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ review_workflow.py│  Orchestrates all steps
└─────────┬─────────┘
          │
    ┌─────┴─────┬─────────────┬──────────────┐
    ▼           ▼             ▼              ▼
 Step 1      Step 2        Step 3         Step 4
 Clone       Pattern       AI             Report
 GitHub      Scanner       Analyzer       Generator
```

### Step 1 — `step1_github_clone.py`
- Uses **GitPython** library to clone GitHub repos
- Walks the folder tree and collects `.py`, `.js`, `.ts`, etc.
- Skips `node_modules`, `.git`, `venv`

### Step 2 — `step2_pattern_scanner.py`
- Uses **Regular Expressions (regex)** to find security issues
- No AI needed — fast and free
- Finds: API keys, passwords, `eval()`, weak crypto

### Step 3 — `step3_ai_analyzer.py`
- Uses **LangChain** to connect to **OpenAI GPT**
- Sends source code to GPT with a structured prompt
- GPT returns JSON with findings, severity, recommendations
- Merges AI results with Step 2 pattern results

### Step 4 — `step4_report_generator.py`
- Uses **ReportLab** to create PDF with bar/pie/gauge charts
- Creates Markdown report as well
- Adds originality notice (unique Report ID per scan)

---

## Technologies Used (For FYP Report)

| Technology | Purpose |
|------------|---------|
| **FastAPI** | Python web framework for REST API |
| **LangChain** | Framework to connect to LLM (GPT) |
| **OpenAI GPT** | AI model that reads and analyzes code |
| **GitPython** | Clone GitHub repositories |
| **ReportLab** | Generate PDF reports with charts |
| **Pydantic** | Validate request/response data structures |
| **Regular Expressions** | Pattern-based security scanning |

---

## API Endpoints

| Method | URL | What it does |
|--------|-----|--------------|
| POST | `/api/review` | Start a new code review |
| GET | `/api/review/{id}` | Get status and results |
| GET | `/api/review/{id}/report?format=pdf` | Download PDF report |
| GET | `/api/review/{id}/report?format=md` | Download Markdown report |
| GET | `/api/health` | Check if server is running |

---

## How Reports Stay Original (No Plagiarism)

Teachers often ask about originality. AI Code Review handles this in **3 ways**:

1. **`originality_helper.py`** builds executive summaries from **actual scan data**
   (repo name, branch, commit, file count, finding counts) — always unique per project.

2. **`prompts.py`** instructs GPT to write in its own words and reference **specific files and lines**
   — not generic security textbook text.

3. Every report gets a unique **Report ID** (SHA-256 hash of repo + commit + timestamp)
   proving it was generated for that specific scan session.

---

## How to Run (Demo for Teachers)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # Add your OPENAI_API_KEY
python run.py
```

Server runs at: **http://localhost:8001**  
API docs at: **http://localhost:8001/docs**

---

## Data Flow Example

```
Input:  https://github.com/user/my-app  (branch: main)
          ↓
Step 1:  Clone to temp_repos/abc123/
          ↓
Step 2:  Found 2 hardcoded secrets in config.py (regex)
          ↓
Step 3:  GPT finds 4 more issues (auth, injection)
          ↓
Step 4:  Save reports/my-app_abc123.pdf with charts
          ↓
Output: JSON response + downloadable PDF report
```

---

## Files Teachers May Ask About

| Question | Answer / File |
|----------|---------------|
| Where is the main logic? | `services/review_workflow.py` |
| How do you clone GitHub? | `services/step1_github_clone.py` |
| How does AI analysis work? | `services/step3_ai_analyzer.py` + `core/prompts.py` |
| How are reports generated? | `services/step4_report_generator.py` |
| What data structures are used? | `models/schemas.py` |
| How is config managed? | `core/config.py` + `.env` |

---

## Author Note

This backend was built as a university FYP project.  
Each module is separated by responsibility (Separation of Concerns design pattern).
