import os
from typing import Optional
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.json_utils import load_json, save_json
from utils.config_utils import get_settings

app_settings = get_settings()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

LOG_FILE = os.path.join(app_settings.PATH_OUTPUT_ROOT, "work_pause_activity_logs.json")
logs = load_json(LOG_FILE, default={})


def save_logs():
    """Save logs to file."""
    save_json(logs, indent=4)


def check_user(user_id):
    if logs.get(user_id) is None:
        logs[user_id] = {"user_info": {"status": "on"}, "user_logs": []}

    return logs[user_id]


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is ready as {bot.user}")
    print("✅ Slash commands synced.")


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
    check_user(user_id)
    if logs[user_id]["user_info"]["status"] == "off":
        msg_leave_off = (
            "🚫 You’re already off right now — looks like you’ve logged a leave or break before. "
            "Use `/back` first before logging another leave!"
        )
        await interaction.response.send_message(msg_leave_off)
        return

    timestamp = datetime.now().isoformat()
    leave_entry = {
        "command": "leave",
        "timestamp": timestamp,
        "args": {
            "reason": reason,
            "compensation_time": compensation_time,
        },
    }
    if duration:
        leave_entry["planned_duration"] = duration

    logs[user_id]["user_logs"].append(leave_entry)
    logs[user_id]["user_info"]["status"] = "off"
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
    check_user(user_id)
    if logs[user_id]["user_info"]["status"] == "on":
        msg_already_on = "🫵 You’re already on! You can only use `/back` after you’ve logged a leave or break."
        await interaction.response.send_message(msg_already_on)
        return

    now = datetime.now()
    timestamp = now.isoformat()

    leave_entry = logs[user_id]["user_logs"][-1]
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

    logs[user_id]["user_logs"].append(back_entry)
    logs[user_id]["user_info"]["status"] = "on"
    leave_entry.update(
        {
            "returned_at": timestamp,
            "duration_seconds": total_seconds,
            "duration": formatted_duration,
        }
    )
    save_logs()

    await interaction.response.send_message(
        f"✅ Logged back for **{interaction.user.name}**.\n"
        f"⏱ Duration since last {leave_entry['command']}: {formatted_duration}."
    )


@bot.tree.command(name="break", description="Log a 20-minute break.")
async def take_break(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    check_user(user_id)
    if logs[user_id]["user_info"]["status"] == "off":
        msg_break_off = (
            "🚫 Hold up! You’re already off because of a previous leave or break. "
            "Use `/back` first before logging another break!"
        )
        await interaction.response.send_message(msg_break_off)
        return

    timestamp = datetime.now().isoformat()
    logs[user_id]["user_logs"].append(
        {"command": "break", "timestamp": timestamp, "duration": "20min"}
    )
    logs[user_id]["user_info"]["status"] = "off"
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
        check_user(user_id)
        user_logs = logs[user_id]["user_logs"]
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
                args = log.get("args", {})
                reason = args.get("reason", "N/A")
                comp = args.get("compensation_time", "N/A")
                planned = log.get("planned_duration")
                planned_txt = f", Planned: {planned}" if planned else ""
                returned_at = log.get("returned_at")
                duration = log.get("duration")
                returned_txt = f", Returned: {returned_at}" if returned_at else ""
                duration_txt = f", Duration: {duration}" if duration else ""
                log_text += f"- 🏃 Leave at {timestamp} (Reason: {reason}, Comp: {comp}{planned_txt}{returned_txt}{duration_txt})\n"
            elif command == "back":
                log_text += f"- 🔙 Back at {timestamp} (Duration: {log.get('duration', 'N/A')})\n"
            elif command == "break":
                returned_at = log.get("returned_at")
                duration = log.get("duration")
                returned_txt = f", Returned: {returned_at}" if returned_at else ""
                duration_txt = f" (Duration: {duration})" if duration else ""
                log_text += f"- ☕ Break at {timestamp}{duration_txt}{returned_txt}\n"

        await interaction.response.send_message(log_text)
        return

    # No user provided: aggregate logs across all users
    aggregated: list[tuple[str, dict]] = []  # (user_id, log)
    for uid, udata in logs.items():
        ulogs = udata["user_logs"]
        for log in ulogs:
            ts = log.get("timestamp")
            if not ts:
                continue
            ts_ok = True
            if start_dt and datetime.fromisoformat(ts) < start_dt:
                ts_ok = False
            if end_dt and datetime.fromisoformat(ts) > end_dt:
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
            args = log.get("args", {})
            reason = args.get("reason", "N/A")
            comp = args.get("compensation_time", "N/A")
            planned = log.get("planned_duration")
            planned_txt = f", Planned: {planned}" if planned else ""
            returned_at = log.get("returned_at")
            duration = log.get("duration")
            returned_txt = f", Returned: {returned_at}" if returned_at else ""
            duration_txt = f", Duration: {duration}" if duration else ""
            log_text += f"- {prefix}🏃 Leave at {timestamp} (Reason: {reason}, Comp: {comp}{planned_txt}{returned_txt}{duration_txt})\n"
        elif command == "back":
            log_text += f"- {prefix}🔙 Back at {timestamp} (Duration: {log.get('duration', 'N/A')})\n"
        elif command == "break":
            returned_at = log.get("returned_at")
            duration = log.get("duration")
            returned_txt = f", Returned: {returned_at}" if returned_at else ""
            duration_txt = f" (Duration: {duration})" if duration else ""
            log_text += (
                f"- {prefix}☕ Break at {timestamp}{duration_txt}{returned_txt}\n"
            )

    await interaction.response.send_message(log_text)


def main():
    """Entry Point for the Program."""
    if not app_settings.DISCORD_BOT_TOKEN:
        raise ValueError(
            "❌ No Discord bot token found. Set DISCORD_BOT_TOKEN in your .env file."
        )

    bot.run(app_settings.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
