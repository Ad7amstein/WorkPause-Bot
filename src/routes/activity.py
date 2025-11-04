"""
Activity tracking cog for the WorkPause Discord bot.

This module defines the `ActivityCog`, which manages slash commands related to user
activity logging — including `/leave`, `/back`, `/break`, and `/show_logs`.

The cog uses a JSON file to persist user data, tracking when users start and end
leaves or breaks, along with optional metadata such as reasons, compensation time,
and durations.

Commands:
    - /leave: Log a leave or break with details.
    - /back: Mark a user as returned from leave/break.
    - /break: Log a standard 20-minute break.
    - /show_logs: Display logs for a user or for all users.

The cog integrates seamlessly with `discord.py` via an extension setup function.
"""

from __future__ import annotations
import os
from typing import Optional, Dict, Any
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.json_utils import load_json, save_json
from utils.config_utils import get_settings


app_settings = get_settings()
LOG_FILE = os.path.join(app_settings.PATH_OUTPUT_ROOT, "work_pause_activity_logs.json")


class ActivityCog(commands.Cog):
    """A Discord Cog for managing work and pause activity logs.

    Handles user interactions via slash commands for logging leave, break,
    and return events. Logs are stored persistently in a JSON file.

    Attributes:
        bot (commands.Bot): The Discord bot instance.
        logs (Dict[str, Dict[str, Any]]): A dictionary of user logs loaded from JSON.
    """

    def __init__(self, bot: commands.Bot):
        """Initialize the ActivityCog.

        Args:
            bot (commands.Bot): The bot instance this cog is attached to.
        """

        self.bot = bot
        self.logs: Dict[str, Dict[str, Any]] = load_json(LOG_FILE, default={})

    def _save_logs(self) -> None:
        """Save the in-memory log data to the JSON file."""

        save_json(self.logs, indent=4)

    def _check_user(self, user_id: str) -> Dict[str, Any]:
        """Ensure a user exists in the log dictionary.

        If a user does not exist in the logs, a new record is initialized.

        Args:
            user_id (str): The Discord user ID.

        Returns:
            Dict[str, Any]: The user’s log data entry.
        """

        if self.logs.get(user_id) is None:
            self.logs[user_id] = {"user_info": {"status": "on"}, "user_logs": []}
        return self.logs[user_id]

    # ========= Slash Commands =========
    @app_commands.command(
        name="leave",
        description=(
            "Log a leave with reason, compensation time, and optional planned duration."
        ),
    )
    @app_commands.describe(
        reason="Reason for leaving",
        compensation_time="Compensation time",
        duration="Planned/expected leave duration (e.g., 30m, 1h) — optional",
    )
    async def leave(
        self,
        interaction: discord.Interaction,
        reason: str,
        compensation_time: str,
        duration: Optional[str] = None,
    ) -> None:
        """Handle the `/leave` command.

        Logs a user's leave event along with details like reason, compensation time,
        and optionally planned duration.

        Args:
            interaction (discord.Interaction): The command interaction object.
            reason (str): The reason for the leave.
            compensation_time (str): The compensation time for the leave.
            duration (Optional[str]): The planned or expected duration of leave.
        """

        user_id = str(interaction.user.id)
        user_data = self._check_user(user_id)

        if user_data["user_info"]["status"] == "off":
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

        user_data["user_logs"].append(leave_entry)
        user_data["user_info"]["status"] = "off"
        self.logs[user_id] = user_data
        self._save_logs()

        msg = (
            f"📝 Logged leave at `{timestamp}` for **{interaction.user.name}**\n"
            f"**Reason:** {reason}\n"
            f"**Compensation:** {compensation_time}"
        )
        if duration:
            msg += f"\n**Planned duration:** {duration}"

        await interaction.response.send_message(msg)

    @app_commands.command(name="back", description="Log that you're back from leave.")
    async def back(self, interaction: discord.Interaction) -> None:
        """Handle the `/back` command.

        Logs that the user has returned from a leave or break, calculates the total
        duration of their absence, and updates their status to "on".

        Args:
            interaction (discord.Interaction): The command interaction object.
        """

        user_id = str(interaction.user.id)
        user_data = self._check_user(user_id)

        if user_data["user_info"]["status"] == "on":
            msg_already_on = "🫵 You’re already on! You can only use `/back` after you’ve logged a leave or break."
            await interaction.response.send_message(msg_already_on)
            return

        now = datetime.now()
        timestamp = now.isoformat()

        # Take the last entry (leave or break) like bot.py
        leave_entry = user_data["user_logs"][-1]
        leave_time = datetime.fromisoformat(leave_entry["timestamp"])  # type: ignore[arg-type]
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

        user_data["user_logs"].append(back_entry)
        user_data["user_info"]["status"] = "on"
        leave_entry.update(
            {
                "returned_at": timestamp,
                "duration_seconds": total_seconds,
                "duration": formatted_duration,
            }
        )

        self.logs[user_id] = user_data
        self._save_logs()

        await interaction.response.send_message(
            f"✅ Logged back for **{interaction.user.name}**.\n"
            f"⏱ Duration since last {leave_entry['command']}: {formatted_duration}."
        )

    @app_commands.command(name="break", description="Log a 20-minute break.")
    async def take_break(self, interaction: discord.Interaction) -> None:
        """Handle the `/break` command.

        Logs a 20-minute break for the user and marks their status as "off".

        Args:
            interaction (discord.Interaction): The command interaction object.
        """

        user_id = str(interaction.user.id)
        user_data = self._check_user(user_id)

        if user_data["user_info"]["status"] == "off":
            msg_break_off = (
                "🚫 Hold up! You’re already off because of a previous leave or break. "
                "Use `/back` first before logging another break!"
            )
            await interaction.response.send_message(msg_break_off)
            return

        timestamp = datetime.now().isoformat()
        user_data["user_logs"].append(
            {"command": "break", "timestamp": timestamp, "duration": "20min"}
        )
        user_data["user_info"]["status"] = "off"
        self.logs[user_id] = user_data
        self._save_logs()

        await interaction.response.send_message(
            f"☕ Logged a 20-minute break for **{interaction.user.name}** at {timestamp}."
        )

    @app_commands.command(
        name="show_logs",
        description="Show activity logs. If no user is provided, shows all users' logs.",
    )
    @app_commands.describe(
        user="User to show logs for (optional)",
        start_date="Start date (YYYY-MM-DD)",
        end_date="End date (YYYY-MM-DD)",
    )
    async def show_logs(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> None:
        """Handle the `/show_logs` command.

        Displays user activity logs within an optional date range. If no user is
        specified, shows aggregated logs for all users.

        Args:
            interaction (discord.Interaction): The command interaction object.
            user (Optional[discord.User]): The user whose logs should be shown.
            start_date (Optional[str]): Optional start date filter (YYYY-MM-DD).
            end_date (Optional[str]): Optional end date filter (YYYY-MM-DD).
        """

        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # If a specific user is provided, keep existing per-user behavior (mirroring bot.py)
        if user:
            user_id = str(user.id)
            user_data = self._check_user(user_id)
            user_logs = user_data["user_logs"]
            filtered_logs = [
                log
                for log in user_logs
                if (
                    not start_dt or datetime.fromisoformat(log["timestamp"]) >= start_dt
                )
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
                    log_text += (
                        f"- ☕ Break at {timestamp}{duration_txt}{returned_txt}\n"
                    )

            await interaction.response.send_message(log_text)
            return

        # No user provided: aggregate logs across all users (mirroring bot.py)
        aggregated: list[tuple[str, dict]] = []  # (user_id, log)
        for uid, udata in self.logs.items():
            ulogs = udata["user_logs"] if udata and "user_logs" in udata else []
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
        aggregated.sort(key=lambda x: x[1]["timestamp"])  # type: ignore[index]

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


async def setup(bot: commands.Bot):
    """Add the `ActivityCog` to the bot.

    This is the required entry point for Discord extensions.

    Args:
        bot (commands.Bot): The bot instance to which the cog will be added.
    """

    await bot.add_cog(ActivityCog(bot))
