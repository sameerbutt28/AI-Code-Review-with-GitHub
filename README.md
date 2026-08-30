# AI Code Review

**See through your code. Secure what matters.**

Automated multi-section GitHub code review for demos and academic delivery.

| Layer | Stack | Default URL |
|-------|--------|-------------|
| Frontend | React + Vite + TypeScript | http://localhost:5173 |
| Backend | FastAPI + LangChain + OpenAI | http://127.0.0.1:8001 |

---

## Quick start (demo)

**Windows:** run `start-backend.bat`, then `start-frontend.bat`  
**Arch Linux / macOS / Linux:** run `./start-backend.sh`, then `./start-frontend.sh`

Then open **http://localhost:5173**

### Arch Linux packages

```bash
sudo pacman -S --needed git python nodejs npm
chmod +x start-backend.sh start-frontend.sh
./start-backend.sh    # terminal 1
./start-frontend.sh   # terminal 2
```

> Full client instructions (including Arch): **[CLIENT_GUIDE.md](./CLIENT_GUIDE.md)** *(local only)*  
> **Client project walkthrough:** **[PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md)** — structure, every file, and how it works

---

## What it does

1. Clones a GitHub repository  
2. Pattern-scans for common issues  
3. Analyses code in chunks with AI across **8 review sections**  
4. Shows dashboard metrics, charts, summary table, and section cards  
5. Exports **PDF** and **Markdown** reports  
6. Caches results per commit so unchanged repos stay consistent  

---

## Project layout

```
Github_Code_Review/
├── CLIENT_GUIDE.md          ← give this to your client
├── FYP_DOCUMENTATION.md     ← university documentation
├── start-backend.bat / .sh
├── start-frontend.bat / .sh
├── backend/                 ← FastAPI API (port 8001)
│   ├── .env.example
│   ├── run.py
│   └── app/
└── frontend/                ← React UI (port 5173)
    └── src/
```

---

## Environment

Copy `backend/.env.example` → `backend/.env` and set:

```env
OPENAI_API_KEY=sk-...
APP_ENV=demo
```

Never commit `.env`.

---

## Development vs demo

| Mode | Command | Notes |
|------|---------|-------|
| Demo (recommended for clients) | `python run.py --demo` | No auto-reload; stabler |
| Development | `python run.py` with `APP_ENV=development` | Auto-reload on code changes |

Frontend:

```bash
cd frontend
npm install
npm run dev      # local UI
npm run build    # production build
npm run preview  # preview built UI (port 4173)
```

---

## Health checks

- API root: http://127.0.0.1:8001/  
- Health: http://127.0.0.1:8001/api/health  
- Docs: http://127.0.0.1:8001/docs  

---

## License / delivery note

Delivered as a local demo application. Cloud deployment, multi-user auth, and a shared database are optional future upgrades—not required to run AI Code Review on a laptop.
