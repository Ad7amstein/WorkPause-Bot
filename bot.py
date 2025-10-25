import os
from typing import Optional
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Import JSON utilities
from src.utils.json_utils import load_json, save_json

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Logs file path
LOG_FILE = "output/work_pause_activity_logs.json"

# Load existing logs (or empty if none)
logs = load_json(LOG_FILE, default={})


def save_logs():
    """Save logs to file."""
    save_json(logs, indent=4)


# ========== EVENTS ==========
@bot.event
async def on_ready():
    await bot.tree.sync()  # Register slash commands
    print(f"✅ Bot is ready as {bot.user}")
    print("✅ Slash commands synced.")


# ========== SLASH COMMANDS ==========
@bot.tree.command(
    name="leave",
    description="Log a leave with reason, compensation time, and optional planned duration.",
)
@app_commands.describe(
    reason="Reason for leaving",
    compensation_time="Compensation time",
    duration="Planned/expected leave duration (e.g., 30m, 1h) — optional",
)
async def leave(
    interaction: discord.Interaction,
    reason: str,
    compensation_time: str,
    duration: Optional[str] = None,
):
    user_id = str(interaction.user.id)
    timestamp = datetime.now().isoformat()

    leave_entry = {
        "command": "leave",
        "timestamp": timestamp,
        "reason": reason,
        "compensation_time": compensation_time,
    }
    if duration:
        # Store user-provided planned/expected duration separately to avoid clashing with actual duration computed on /back
        leave_entry["planned_duration"] = duration

    logs[user_id] = logs.get(user_id, []) + [leave_entry]
    save_logs()

    msg = (
        f"📝 Logged leave at `{timestamp}` for **{interaction.user.name}**\n"
        f"**Reason:** {reason}\n"
        f"**Compensation:** {compensation_time}"
    )
    if duration:
        msg += f"\n**Planned duration:** {duration}"

    await interaction.response.send_message(msg)


@bot.tree.command(name="back", description="Log that you're back from leave.")
async def back(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    now = datetime.now()
    timestamp = now.isoformat()

    user_logs = logs.get(user_id, [])
    last_leave_index = None

    for i in range(len(user_logs) - 1, -1, -1):
        entry = user_logs[i]
        if entry.get("command") != "leave":
            continue
        leave_ts = datetime.fromisoformat(entry["timestamp"])

        has_back_after = any(
            log.get("command") == "back"
            and datetime.fromisoformat(log["timestamp"]) > leave_ts
            for log in user_logs[i + 1 :]
        )

        if not has_back_after:
            last_leave_index = i
            break

    if last_leave_index is None:
        logs[user_id] = user_logs
        save_logs()
        await interaction.response.send_message(
            f"✅ Logged back for **{interaction.user.name}** at {timestamp} (no unmatched leave found)."
        )
        return

    leave_entry = user_logs[last_leave_index]
    leave_time = datetime.fromisoformat(leave_entry["timestamp"])
    delta = now - leave_time
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    formatted_duration = (
        f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
    )

    back_entry = {
        "command": "back",
        "timestamp": timestamp,
        "duration_seconds": total_seconds,
        "duration": formatted_duration,
    }

    user_logs.append(back_entry)
    leave_entry.update(
        {
            "returned_at": timestamp,
            "duration_seconds": total_seconds,
            "duration": formatted_duration,
        }
    )

    logs[user_id] = user_logs
    save_logs()

    await interaction.response.send_message(
        f"✅ Logged back for **{interaction.user.name}**.\n"
        f"⏱ Duration since last leave: {formatted_duration}."
    )


@bot.tree.command(name="break", description="Log a 20-minute break.")
async def take_break(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    timestamp = datetime.now().isoformat()
    logs[user_id] = logs.get(user_id, []) + [
        {"command": "break", "timestamp": timestamp, "duration": "20min"}
    ]
    save_logs()

    await interaction.response.send_message(
        f"☕ Logged a 20-minute break for **{interaction.user.name}** at {timestamp}."
    )


@bot.tree.command(
    name="show_logs",
    description="Show activity logs. If no user is provided, shows all users' logs.",
)
@app_commands.describe(
    user="User to show logs for (optional)",
    start_date="Start date (YYYY-MM-DD)",
    end_date="End date (YYYY-MM-DD)",
)
async def show_logs(
    interaction: discord.Interaction,
    user: Optional[discord.User] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    # If a specific user is provided, keep existing per-user behavior
    if user:
        user_id = str(user.id)
        user_logs = logs.get(user_id, [])
        filtered_logs = [
            log
            for log in user_logs
            if (not start_dt or datetime.fromisoformat(log["timestamp"]) >= start_dt)
            and (not end_dt or datetime.fromisoformat(log["timestamp"]) <= end_dt)
        ]

        if filtered_logs is None or len(filtered_logs) == 0:
            await interaction.response.send_message(
                f"No logs found for **{user.name if user else interaction.user.name}**."
            )
            return

        log_text = f"🗂 Logs for **{user.name}**:\n"
        for log in filtered_logs:
            command = log["command"]
            timestamp = log["timestamp"]
            if command == "leave":
                planned = log.get("planned_duration")
                planned_txt = f", Planned: {planned}" if planned else ""
                log_text += f"- 🏃 Leave at {timestamp} (Reason: {log.get('reason')}, Comp: {log.get('compensation_time')}{planned_txt})\n"
            elif command == "back":
                log_text += (
                    f"- 🔙 Back at {timestamp} (Duration: {log.get('duration', 'N/A')})\n"
                )
            elif command == "break":
                log_text += f"- ☕ Break at {timestamp} (Duration: {log.get('duration')})\n"

        await interaction.response.send_message(log_text)
        return

    # No user provided: aggregate logs across all users
    aggregated: list[tuple[str, dict]] = []  # (user_id, log)
    for uid, ulogs in logs.items():
        for log in ulogs:
            ts_ok = True
            if start_dt and datetime.fromisoformat(log["timestamp"]) < start_dt:
                ts_ok = False
            if end_dt and datetime.fromisoformat(log["timestamp"]) > end_dt:
                ts_ok = False
            if ts_ok:
                aggregated.append((uid, log))

    if not aggregated:
        await interaction.response.send_message("No logs found.")
        return

    # Sort by timestamp ascending for readability
    aggregated.sort(key=lambda x: x[1]["timestamp"])

    log_text = "🗂 Logs for all users:\n"
    for uid, log in aggregated:
        user_mention = f"<@{uid}>"
        command = log["command"]
        timestamp = log["timestamp"]
        prefix = f"{user_mention} — "
        if command == "leave":
            planned = log.get("planned_duration")
            planned_txt = f", Planned: {planned}" if planned else ""
            log_text += f"- {prefix}🏃 Leave at {timestamp} (Reason: {log.get('reason')}, Comp: {log.get('compensation_time')}{planned_txt})\n"
        elif command == "back":
            log_text += f"- {prefix}🔙 Back at {timestamp} (Duration: {log.get('duration', 'N/A')})\n"
        elif command == "break":
            log_text += (
                f"- {prefix}☕ Break at {timestamp} (Duration: {log.get('duration')})\n"
            )

    await interaction.response.send_message(log_text)


# ========== RUN BOT ==========
token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError(
        "❌ No Discord bot token found. Set DISCORD_BOT_TOKEN in your .env file."
    )

bot.run(token)
