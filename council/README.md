# JARVIS AI Council

One task → 15 models respond simultaneously → Claude Opus synthesizes the verdict.

## Setup (3 steps)

**Step 1 — Install Python dependencies**
```
pip install -r requirements.txt
```

**Step 2 — Add your API keys**
```
copy council.env.example council.env
```
Open `council.env` and paste your keys.

**Step 3 — Run the council**
```
python council.py
```

## Usage

```
python council.py
Enter your task: Write a sales strategy for Aliyar Solutions targeting healthcare

⚡ Sending task to all 14 council members simultaneously...

  ✅ [01] Claude Opus 4.6        Senior Strategic Advisor
  ✅ [02] Claude Sonnet 4.6      Operations Intelligence
  ✅ [03] MiniMax M2.7           Creative & Content Director
  ✅ [04] DeepSeek V4 Flash      Code & Engineering Lead
  ... all 14 respond ...

🏆 COUNCIL VERDICT
══════════════════════════════════════════════════════════════════
[Final synthesized answer from Claude Opus 4.8]
```

## Or pass task directly

```
python council.py "What pricing model should Aliyar Solutions use for enterprise clients?"
```
