# Tech News AI Agent 🤖

**Author: taha deab**

> 📰 An autonomous AI agent built with Python that fetches the latest technology articles from configurable RSS feeds, summarizes them using an LLM API, formats them into a polished daily report, and delivers it automatically via a Telegram Bot.

**Features at a glance:**

- 🌍 **Fully bilingual** — supports Arabic, English, or both languages simultaneously
- 📡 **Multi-source RSS aggregation** — TechCrunch, The Verge, Wired, Ars Technica, Hacker News (fully customizable)
- 🧠 **LLM-powered summarization** — parallel processing (6x faster) with an analytical daily overview
- 📨 **Telegram delivery** — auto-split long reports to respect Telegram's 4096-character limit
- 🗓 **Daily scheduling** — runs automatically every day at a configurable time
- 🔑 **Keyword filtering** — include/exclude articles by keyword for a personalized digest
- 🎨 **Local report archives** — beautiful HTML reports (RTL for Arabic, LTR for English) + Markdown copies

---

## Table of Contents

- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Agent](#running-the-agent)
- [Testing](#testing)
- [Report Outputs](#report-outputs)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## How It Works

The agent runs a daily pipeline of four stages:

| Stage | What Happens | Module |
|-------|--------------|--------|
| 1. Collection | Fetches articles from the RSS feeds listed in `config.json` | `rss_collector.py` |
| 2. Filtering | Applies include/exclude keyword filters and removes duplicates | `rss_collector.py` |
| 3. Summarization | Summarizes each article in parallel and generates an analytical intro via any OpenAI-compatible LLM API | `llm_summarizer.py` |
| 4. Delivery | Formats the report in Markdown, HTML, and Telegram formats, saves it locally, and sends it via the Telegram Bot API | `report_formatter.py`, `telegram_sender.py`, `scheduler.py` |

**Language modes** (set via the `language` key in `config.json`):

| Value | Result |
|-------|--------|
| `"both"` *(default)* | A single Telegram report combining Arabic 🇸🇦 and English 🇬🇧, plus two separate local files (`_ar` and `_en`) |
| `"Arabic"` | A fully Arabic report |
| `"English"` | A fully English report |

---

## Project Structure

```
tech_news_agent/
├── main.py              # Main entry point (scheduler / --once / --setup-bot)
├── config.json          # Fully customizable configuration file
├── rss_collector.py     # RSS feed collection and keyword filtering
├── llm_summarizer.py    # LLM API summarization (parallel, 6x faster)
├── report_formatter.py  # Report formatting (Markdown / HTML / Telegram)
├── telegram_sender.py   # Telegram Bot delivery with error handling
├── scheduler.py         # Daily scheduling via APScheduler
├── test_agent.py        # Comprehensive test suite
├── requirements.txt     # Python dependencies
├── LICENSE              # MIT License
└── reports/             # Generated reports (created automatically)
```

---

## Prerequisites

- **Python 3.10** or later — [python.org](https://www.python.org/downloads/)

---

## Installation

```bash
# 1. Clone or extract the project
git clone https://github.com/tahadeab/tech-news-ai-agent.git
cd tech_news_agent

# 2. (Optional but recommended) Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Open `config.json` and fill in the required settings:

### 1. Language (new!)

```json
"language": "both"
```

### 2. LLM API Key

Any service compatible with the OpenAI Chat Completions API works (OpenAI, Groq, OpenRouter, LM Studio, ...):

```json
"llm": {
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-your-api-key",
  "model": "gpt-4o-mini",
  "max_tokens": 2000,
  "temperature": 0.3
}
```

### 3. Telegram Bot

**Step 1** — Create a new bot via [@BotFather](https://t.me/BotFather):

1. Open [@BotFather](https://t.me/BotFather) and send `/newbot`
2. Choose a name; BotFather will give you a `bot_token`

**Step 2** — Set the chat ID interactively:

```bash
python3 main.py --setup-bot
```

This tool asks you to send a message to your bot, then automatically writes the `chat_id` into `config.json`.

### 4. RSS Sources and Keywords

```json
"rss_feeds": [
  { "name": "TechCrunch", "url": "https://techcrunch.com/feed/" }
],

"keywords": {
  "include": ["AI", "OpenAI", "cybersecurity"],   // empty = all articles
  "exclude": ["sponsored", "ads"]                  // articles to exclude
}
```

**Usage examples:**

- `include: ["AI", "machine learning"]` — a digest focused on artificial intelligence only
- `exclude: ["sponsored", "review"]` — skip promotional posts and product reviews

### 5. Scheduling

```json
"scheduler": {
  "enabled": true,
  "send_time": "08:00",
  "timezone": "Asia/Riyadh"
}
```

---

## Running the Agent

### Mode 1: One-off run (testing)

```bash
python3 main.py --once
```

Executes a full cycle immediately (collect → filter → summarize → format → save). If `bot_token` and `chat_id` are empty, Telegram delivery is skipped and the report is saved locally only — perfect for testing.

### Mode 2: Continuous mode with daily scheduling

```bash
python3 main.py
```

The agent stays alive in the background and sends the report every day at the time configured in `config.json`.

### Mode 3: Telegram setup helper

```bash
python3 main.py --setup-bot
```

### Running permanently as a systemd service (Linux)

```bash
sudo tee /etc/systemd/system/tech-news-agent.service <<'EOF'
[Unit]
Description=Tech News AI Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/taha/tech_news_agent
ExecStart=/home/taha/tech_news_agent/venv/bin/python main.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now tech-news-agent
sudo systemctl status tech-news-agent
```

---

## Testing

```bash
python3 test_agent.py
```

The test suite exercises all three language modes (`both` / `English` / `Arabic`) and verifies feed collection, bilingual summary quality, Telegram message length limits, and HTML text direction.

---

## Report Outputs

Reports are saved in the `reports/` directory:

| File | Description |
|------|-------------|
| `report_YYYY-MM-DD_ar.html` | Arabic report with RTL layout |
| `report_YYYY-MM-DD_ar.md` | Arabic report in Markdown |
| `report_YYYY-MM-DD_en.html` | English report with LTR layout |
| `report_YYYY-MM-DD_en.md` | English report in Markdown |

With `language: "both"`, a single bilingual Telegram report (🇸🇦 Arabic + 🇬🇧 English) is sent and automatically split into chunks that never exceed Telegram's 4096-character limit.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `llm.api_key is not configured` | Add your API key to `config.json` |
| Telegram error 400 | Run `python3 main.py --setup-bot` to fix the `chat_id` |
| Messages exceeding 4096 chars | Handled automatically — no action needed |
| An RSS source fails | Verify the URL in a browser; some feeds require a custom User-Agent |
| Summaries show "Summary unavailable" | Double-check `base_url`, `api_key`, and the model name |
| Scheduled run does not send | Ensure `scheduler.enabled` is `true` and the process is still running (Ctrl+C kills it) |

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
