# Marksheet: setup and run guide

How to move this project to a new Windows laptop that has nothing installed, and run it end to end.

**Time needed:** about 15 minutes, most of it downloads.
**What you'll have at the end:** the app running at http://localhost:8000.

---

## 1. What the project needs

### 1.1 Software to install yourself (one time)

| # | Software | Version | Why | Download |
|---|---|---|---|---|
| 1 | **Python** | 3.11 or newer (**3.13 recommended**, tested with 3.13.5) | Runs the backend and the AI pipeline | https://www.python.org/downloads/ |
| 2 | **Node.js** | 20.19 or newer (**LTS 22 or 24 recommended**, tested with 24.18) | Builds the web interface | https://nodejs.org/ |
| 3 | A web browser | Chrome, Edge or Firefox | To use the app | already on Windows |

Not needed: Git, a database server, Docker, a GPU, or CUDA. The database is a file, and the AI runs in Google's cloud.

### 1.2 Accounts and keys

| Item | Why | Where |
|---|---|---|
| **Google Gemini API key** (free) | Reads the handwriting, grades the answers, compares meaning | https://aistudio.google.com/apikey |

### 1.3 Installed automatically by `setup.bat`

**Python packages** (exact versions pinned in `backend/requirements.txt`):

| Package | Version | Purpose |
|---|---|---|
| fastapi | 0.141.1 | Web API framework |
| uvicorn[standard] | 0.54.0 | Web server |
| python-multipart | 0.0.32 | File uploads |
| pydantic / pydantic-settings | 2.13.5 / 2.15.0 | Data validation, reading `.env` |
| sqlmodel / SQLAlchemy | 0.0.47 / 2.0.54 | SQLite database access |
| google-genai | 2.25.0 | Gemini API client |
| pymupdf | 1.28.2 | PDF to page images |
| opencv-python-headless | 5.0.0.93 | Image cleanup (straightening, contrast) |
| pillow | 12.3.0 | Image loading, phone photo rotation |
| numpy | 2.5.3 | Image arrays |
| rapidfuzz | 3.14.6 | Measures how well the two handwriting readers agree |

**Frontend packages** (pinned in `frontend/package-lock.json`): React 19, Vite 8, TypeScript 6.

### 1.4 Internet access
- **During setup:** to download the packages above (about 150 MB).
- **While using the app:** every evaluation calls the Gemini API. Page fonts load from Google Fonts; without internet the app falls back to system fonts.

---

## 2. On the OLD laptop: make the zip

**Don't zip the folder by hand.** Right-click → Compress would include two folders (about 420 MB) that **don't work on another PC**: `backend\.venv` has this laptop's file paths built in, and `frontend\node_modules` is rebuilt anyway.

Use the included script instead. Open PowerShell in the project folder and run:

```powershell
cd C:\Users\aditya.patil\Downloads\Ai_Project_Test
powershell -ExecutionPolicy Bypass -File .\make-zip.ps1
```

This creates **`Marksheet.zip`** (about 1 MB) inside the project folder. Copy it to the new laptop (USB, Google Drive, email).

| Option | Command | Result |
|---|---|---|
| Keep the API key private (**recommended**) | `.\make-zip.ps1` | `backend\.env` is left out; setup asks for the key on the new laptop |
| Take the key along | `.\make-zip.ps1 -IncludeKey` | No key prompt, but anyone with the zip can use your key |

**Included in the zip:** all code, the rubric, the question paper, your sample pages, `outputs/`, and **`backend/storage/`** (database with your rubrics and evaluation history, plus the cache).

> If you already zipped the folder by hand, that's fine too: `setup.bat` detects the broken `.venv` and rebuilds it. The zip is just bigger.

---

## 3. On the NEW laptop: install

### Step 1: Install Python
1. Download the latest **Python 3.13** Windows installer (64-bit) from https://www.python.org/downloads/.
2. Run it. On the first screen, **tick "Add python.exe to PATH"**. This is the most commonly missed step.
3. Click **Install Now** and wait for "Setup was successful".

### Step 2: Install Node.js
1. Download the **LTS** Windows installer (.msi) from https://nodejs.org/.
2. Run it and click **Next** through the screens with the default options.
   You can leave "Automatically install the necessary tools" (Chocolatey) unticked.

### Step 3: Check both installed
Open a **new** PowerShell window (Start → type `powershell` → Enter) and run:
```powershell
python --version     # should print Python 3.13.x
node --version       # should print v22.x or v24.x
```
If either says "not recognized", see [Troubleshooting](#6-troubleshooting).

### Step 4: Unzip the project
1. Right-click `Marksheet.zip` → **Extract All…**
2. Pick a simple location, for example `C:\Users\<you>\Documents\`
   This creates `…\Documents\Ai_Project_Test\`.
3. Avoid OneDrive-synced folders if you can; syncing can lock files during install.

### Step 5: Get a Gemini API key (skip if you zipped with `-IncludeKey`)
1. Open https://aistudio.google.com/apikey and sign in with a **personal Gmail** account. Work accounts are often blocked by company policy.
2. Click **Create API key**.
   If you see *"Unable to create API key"*: go to https://console.cloud.google.com/projectcreate, create a project (e.g. `answer-sheet-eval`, parent "No organization"), come back and choose **Create API key in existing project**.
3. Copy the key. Keep it for the next step.

### Step 6: Run the installer
1. Open the `Ai_Project_Test` folder.
2. **Double-click `setup.bat`**.
   If a blue "Windows protected your PC" box appears, click **More info → Run anyway**.
3. It runs these steps automatically, taking 2–5 minutes:
   ```
   ==> Checking Python                 → Python 3.13.x OK
   ==> Checking Node.js                → Node.js v24.x OK
   ==> Setting up the Python environment   (creates backend\.venv, installs packages)
   ==> Installing frontend packages (npm)
   ==> Building the web interface
   ==> Configuring the Gemini API key  → paste your key when asked, press Enter
   ==> Testing the installation        → Backend imports OK / Gemini key OK
   Setup complete.
   ```
4. Press any key to close the window.

`setup.bat` is safe to run again at any time. It repairs or skips whatever is already done.

---

## 4. Run the app

1. **Double-click `run.bat`.**
2. A black window opens, and after about 3 seconds your browser opens **http://localhost:8000**.
3. **Keep the black window open** while using the app. Close it (or press Ctrl + C) to stop.

If `run.bat` is double-clicked while the app is already running, it just opens the browser.

### Using it
1. **Evaluate** page: drag in the answer-sheet pages (JPG, PNG or PDF), put them in page order, and choose the rubric.
2. Click **Evaluate**. The progress bar runs through Extract, Structure, Score and Confidence. The first run of a new sheet takes about 20–60 s.
3. Review each question: what was read from the handwriting, ✓ / ½ / ✗ per mark point with evidence, the score, and the confidence label with its reason.
4. Filter with **Needs review**. Download with **CSV** or **JSON**.
5. **Rubrics** page: view, edit or create answer keys.

### Other ways to run

| Goal | Command (from the project folder) |
|---|---|
| Normal start without `run.bat` | `powershell -ExecutionPolicy Bypass -File .\run.ps1` |
| Developer mode (page reloads as you edit code) | `powershell -ExecutionPolicy Bypass -File .\run.ps1 -Dev` then open http://localhost:5173 |
| Command line only (writes `outputs\results.json` + `.csv`) | `cd backend` then `.\.venv\Scripts\python.exe cli.py ..\data\samples` |
| Backend only, by hand | `cd backend` then `.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` |
| API documentation | open http://localhost:8000/docs while running |

---

## 5. Where things are

```
Ai_Project_Test/
├── setup.bat / setup.ps1    one-time installer (new laptop)
├── run.bat / run.ps1        start the app
├── make-zip.ps1             make a clean, portable zip
├── SETUP.md                 this guide
├── README.md                project overview
├── APPROACH.md              approach note (assignment deliverable)
├── backend/
│   ├── .env                 your Gemini key + model settings  (private: don't share)
│   ├── .env.example         template for .env
│   ├── requirements.txt     Python packages (exact versions)
│   ├── cli.py               command-line runner
│   ├── app/                 FastAPI app + pipeline (extract → segment → score → confidence)
│   └── storage/             ← ALL app data
│       ├── app.db           SQLite database: rubrics + evaluation history/results
│       ├── cache.db         Gemini response cache (safe to delete; makes re-runs instant)
│       └── evals/<id>/      cleaned page images per evaluation
├── frontend/                React + Vite web interface (src/ = code, dist/ = built site)
├── data/
│   ├── QUESTION_PAPER.md    questions + short answer key
│   ├── SOURCE.md            where the sample sheet came from
│   ├── rubrics/             rubric JSON (loaded into the database on first start)
│   └── samples/             handwritten answer pages
└── outputs/                 results.json / results.csv (assignment deliverable)
```

**Settings in `backend/.env`:**

| Setting | Default | Meaning |
|---|---|---|
| `GEMINI_API_KEY` | (your key) | Required |
| `PRIMARY_MODELS` | `gemini-3.8-flash,gemini-3.5-flash,gemini-flash-latest,gemini-3.5-flash-lite` | Reader + grader, tried in order; the next is used when one is busy |
| `CROSSCHECK_MODELS` | `gemini-3.5-flash-lite,gemini-flash-lite-latest,gemini-3.1-flash-lite` | Second, independent handwriting reader |
| `EMBED_MODEL` | `gemini-embedding-2` | Meaning-similarity check |
| `JUDGE_RUNS` | `3` | Grading runs per sheet (their agreement feeds the confidence label) |

---

## 6. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `python` / `node` "is not recognized" | Not on PATH, or the terminal was opened before installing | Close **all** terminals and open a new one. For Python, re-run the installer → **Modify** → tick "Add Python to environment variables" |
| `python --version` opens the Microsoft Store | Windows' fake python alias | Settings → Apps → Advanced app settings → **App execution aliases** → turn off both "python" entries, then open a new terminal |
| "running scripts is disabled on this system" | Windows blocks `.ps1` files by default | Use the `.bat` files, or run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `[Errno 10048] … only one usage of each socket address` | The app is already running (port 8000 in use) | Use the open app at http://localhost:8000, or close the other black window first |
| Browser shows `ERR_CONNECTION_REFUSED` | The server isn't running | Start `run.bat` and keep its window open |
| Evaluation fails with **503** / "high demand" | Google's free tier is overloaded | Wait a minute and try again. Pages already read are cached |
| **429** / "quota" / "rate limit" | Free-tier per-minute or per-day limit reached | Wait a minute (or until the next day for the daily limit) |
| **404** "model … no longer available" | Google retired a model name | Open https://aistudio.google.com, check the current model names, and update `PRIMARY_MODELS` / `CROSSCHECK_MODELS` in `backend\.env` |
| "API key not valid" / 400 / 403 | Wrong or deleted key | Put a fresh key in `backend\.env` (`GEMINI_API_KEY=...`, no quotes or spaces) and restart `run.bat` |
| `pip install` or `npm ci` fails | No internet, company proxy, or antivirus | Check the connection, try another network, then re-run `setup.bat` |
| Page looks old after editing code | The built site is out of date | `cd frontend` → `npm run build`, then restart `run.bat` |
| Want to start fresh (erase history) | | Stop the app, delete `backend\storage\`, then start again (the rubric reloads from `data\rubrics`) |

---

## 7. Security checklist
- `backend\.env` holds your API key. Don't share it, commit it to GitHub, or send the zip made with `-IncludeKey`.
- If the key was ever pasted anywhere public (chat, email, screenshot), delete it at https://aistudio.google.com/apikey and create a new one.
- On Gemini's free tier, Google may use your inputs to improve its products. Use sample or synthetic scripts, not real students' papers.
- The app listens on `localhost` only, so other computers on your network can't reach it.
