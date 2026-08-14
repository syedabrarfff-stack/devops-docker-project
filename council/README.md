# JARVIS AI Council — Aliyar Solutions

**14 models. One task. One verdict.**

Every task fires all 14 AI models simultaneously. AWS Bedrock Claude Opus 4.8 synthesizes the final answer — superior to any individual model.

---

## First-Time Setup (Windows)

### Step 1 — Clone the repo in VS Code

```
git clone https://github.com/syedabrarfff-stack/devops-docker-project
cd devops-docker-project
```

Or in VS Code: **Source Control → Clone Repository**

### Step 2 — Install dependencies

Open a terminal in VS Code (`Ctrl+`\`), navigate to the `council` folder and run:

```
cd council
pip install -r requirements.txt
```

### Step 3 — Create your `.env` file (one-time, never re-do)

**Option A — Double-click `SETUP_JARVIS.bat`** (easiest)
- Opens a template you fill in with your keys
- Writes `.env` automatically

**Option B — Manual**
```
copy council.env.example .env
```
Open `.env` in Notepad and replace each `PASTE_YOUR_..._HERE` with your actual key.

### Step 4 — Run the council

```
python council.py
```

Or just double-click `run.bat`.

---

## Running from VS Code (one click)

Open the project in VS Code, then press `Ctrl+Shift+P` → **Tasks: Run Task** → **Council: Ask the AI Council**

This runs the council directly from VS Code's integrated terminal.

---

## API Keys — Where to Get Them

| Provider | Where | Key Format |
|---|---|---|
| **AWS Bedrock** (primary) | AWS Console → Bedrock → API Keys | `ABSK...` long key |
| AWS IAM (alternative) | AWS Console → IAM → Access Keys | `AKIA...` |
| Anthropic (fallback) | console.anthropic.com → API Keys | `sk-ant-...` |
| NVIDIA NIM | build.nvidia.com → Get API Key | `nvapi-...` |
| Google Gemini | aistudio.google.com → Get API Key | `AIza...` |
| OpenRouter | openrouter.ai → Keys | `sk-or-...` |

**One NVIDIA key works for all 10 NIM models.** Paste the same key in all 10 `NVIDIA_KEY_*` slots.

---

## The 14 Council Members

| # | Model | Provider | Role |
|---|---|---|---|
| SYNTH | Claude Opus 4.8 | AWS Bedrock | **Chief Synthesizer** |
| 1 | Claude Sonnet 4.6 | Anthropic | Operations & Strategy |
| 2 | Llama 4 Maverick | NVIDIA NIM | Advanced Reasoning |
| 3 | Llama 4 Scout | NVIDIA NIM | Fast Intelligence |
| 4 | Llama 3.3 70B | NVIDIA NIM | Deep Analysis |
| 5 | Qwen 2.5 Coder 32B | NVIDIA NIM | Code & Engineering |
| 6 | Moonshot Kimi K2.6 | NVIDIA NIM | Long-Context |
| 7 | Mistral Medium 3 | NVIDIA NIM | Risk & Compliance |
| 8 | Z AI Glam 5.1 | NVIDIA NIM | Innovation |
| 9 | DeepSeek V4 Flash | NVIDIA NIM | Lightning Code |
| 10 | DeepSeek V4 Pro | NVIDIA NIM | Deep Research |
| 11 | MiniMax M2.7 | NVIDIA NIM | Creative Strategy |
| 12 | Gemini 2.5 Pro | Google | Market Intelligence |
| 13 | AI21 Jamba Large | OpenRouter | Long-Context Documents |

---

## Synthesizer Priority (automatic fallback)

```
1. AWS Bedrock API Key  →  longest-lived, never expires
2. AWS IAM credentials  →  standard AWS auth
3. Anthropic direct     →  last resort fallback
```

---

## Usage

```bash
# Interactive mode (ask multiple questions)
python council.py

# Single task mode
python council.py "Build a sales strategy for healthcare clients"
```

Sessions are saved to `council/sessions/council_TIMESTAMP.txt`.

---

## Troubleshooting

**Bedrock fails with AccessDeniedException**
- Log into AWS Console → Bedrock → Model Access → Enable Claude models for `ap-south-1`

**NVIDIA models show [SKIPPED]**
- Check your key starts with `nvapi-` (not `sk-or-` or anything else)

**All models fail**
- Run `pip install -r requirements.txt` again
- Verify `.env` exists in the `council/` folder

**Wrong directory error**
- Always run from inside the `council/` folder: `cd council` first
