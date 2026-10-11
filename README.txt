GAMEGURU.AI Telegram worker
============================

Files:
- bot.py: polling worker and HTML-derived heuristic engines
- requirements.txt: dependencies

Setup:
1. Install Python 3.10+.
2. `python -m venv .venv`
3. Activate the environment, then `pip install -r requirements.txt`
4. Set environment variables:
   - TELEGRAM_BOT_TOKEN: token from BotFather
   - TELEGRAM_CHANNEL_ID: channel ID such as @your_channel (bot must be an admin)
   - GAME_TYPE: 1M (default) or 30S
   - STICKER_FILE_ID: optional sticker file ID
5. Run `python bot.py`.

Background operation:
- Linux VPS: run under systemd or `nohup`; for production use systemd so it restarts after reboot.
- PaaS: configure a persistent worker process. A web request server is not required for this bot.
- Keep `gameguru_state.json` on persistent storage. It prevents duplicate issue sends and stores the pending prediction/stats.
- Only one worker instance should run for a given channel/type to avoid duplicate messages.

Important:
- The HTML's displayed confidence values are heuristic scores, not calibrated probabilities.
- The source page contains several algorithms with hard-coded historical patterns; these are reproduced as heuristic logic, not validated forecasting.
- The external draw API can change or be unavailable. The worker logs failures and retries.
