# WorkPause-Bot

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![discord.py](https://img.shields.io/badge/discord.py-2.6.4-5865F2?logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://makeapullrequest.com)
[![Made with Love](https://img.shields.io/badge/Made%20with-%F0%9F%92%9A-blue)](https://github.com/Ad7amstein/WorkPause-Bot)

A friendly Discord bot to help you log time-off activities, breaks, and returns—keeping your team in sync and your records tidy. ☕⏱

![WorkPause Bot Logo](assets/logo.png)

> Tip: If the logo doesn’t show, make sure `assets/logo.png` exists in your clone.

## Introduction

WorkPause-Bot is a simple, lightweight Discord bot for tracking leave and return activities inside your server. It supports intuitive slash commands, stores logs locally as JSON, and is easy to run on your own machine or server.

Use it to:

- Log a leave with a reason and compensation time
- Mark when you’re back and get the elapsed time automatically
- Log a quick 20-minute coffee break
- Review logs for a person or everyone, optionally filtered by date

## Demo 🎥

Watch a short demonstration of the bot in action:

- ▶️ Video: [assets/demo.mp4](assets/demo.mp4)

![Demo GIF](assets/demo.gif)

## Features ✨

- Slash commands for clarity and ease of use
  - `/leave` — log time off with reason and compensation time (optional planned duration)
  - `/back` — mark your return and auto-calculate duration since last leave
  - `/break` — log a standard 20-minute break
  - `/show_logs` — view logs for a user or for everyone, with optional date filters
- Robust JSON logging (auto-repairs malformed JSON when reading)
- Local, portable storage at `output/work_pause_activity_logs.json`
- Minimal setup: just your Discord bot token and Python 3.12+

## Project Structure 🗂

```text
WorkPause-Bot/
├─ bot.py                          # Main bot entrypoint (slash commands and logic)
├─ requirements.txt                # Runtime dependencies
├─ pyproject.toml                  # Project metadata (Python 3.12+)
├─ LICENSE                         # MIT license
├─ README.md                       # You’re reading it!
├─ assets/
│  ├─ logo.png                    # Project logo (referenced in README)
│  └─ demo.mp4                    # Short demo video (linked in README)
├─ scripts/
│  ├─ create_env.sh               # Helper: create & activate venv, install deps
│  └─ run_app.sh                  # Helper: install package (editable) & run bot
├─ output/
│  └─ work_pause_activity_logs.json  # Logs (created at runtime)
└─ src/
   └─ utils/
      └─ json_utils.py            # Load/save JSON with auto-repair fallback
```

## Installation 🛠

Prerequisites:

- Python 3.12 or newer
- A Discord application and bot token (from the Discord Developer Portal)

1. Clone the repo

```bash
git clone https://github.com/Ad7amstein/WorkPause-Bot.git
cd WorkPause-Bot
```

1. Create a virtual environment and install dependencies (two options)

- Using the provided helper script (tries Python 3.12 by default):

```bash
bash scripts/create_env.sh            # or: bash scripts/create_env.sh 3.12
```

- Or do it manually:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

1. Configure environment variables

Create a `.env` file in the project root with your bot token:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

1. (Recommended) Enable Message Content Intent

This bot sets `intents.message_content = True`. In the Discord Developer Portal, go to your application → Bot → Privileged Gateway Intents → enable “Message Content Intent”.

## Usage 🚀

Start the bot (two options):

- Using the helper script:

```bash
bash scripts/run_app.sh
```

- Or directly with Python:

```bash
source .venv/bin/activate
python bot.py
```

Once the bot is running, it will sync slash commands automatically. In any server where the bot is present, try:

### Slash Commands

- `/leave reason:<text> compensation_time:<text> duration:<optional>`
  - Example: `/leave reason:Doctor appointment compensation_time:1h duration:45m`
- `/back`
  - Marks your return and replies with the elapsed time (e.g., “32m 10s”).
- `/break`
  - Logs a standard 20-minute break.
- `/show_logs user:<optional> start_date:<YYYY-MM-DD> end_date:<YYYY-MM-DD>`
  - Example (me only): `/show_logs`
  - Example (someone else): `/show_logs user:@alice`
  - Example (filtered): `/show_logs start_date:2025-10-01 end_date:2025-10-31`

### Where are logs stored?

All activity is saved locally at:

```text
output/work_pause_activity_logs.json
```

The file is created automatically on first use. JSON reads use a repair step for resilience, falling back to strict parsing if needed.

## Configuration Tips ⚙️

- Invite the bot to your server with the `bot` and `applications.commands` scopes.
- Ensure the bot has permission to read and send messages in the channels you’ll use.
- If you change the bot’s scopes or intents, restart the bot to re-sync commands.

## Contributing 🤝

Contributions are welcome! Here’s a quick path:

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/awesome-thing`
3. Make your changes (keep them focused and documented)
4. Run and test locally
5. Commit with a clear message and open a Pull Request

If you’re not sure where to start, open an issue and we’ll help you scope it.

## License 📄

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙌

- [discord.py](https://discordpy.readthedocs.io/) — the excellent Python library for Discord bots
- [python-dotenv](https://github.com/theskumar/python-dotenv) — for easy `.env` management
- [json-repair](https://github.com/mangiucugna/json-repair) — makes JSON loading more resilient

---

Got ideas or feedback? Open an issue or PR — we’d love to hear from you! 💬
