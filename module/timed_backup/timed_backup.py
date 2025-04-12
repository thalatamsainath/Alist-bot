# -*- coding: UTF-8 -*-
import datetime
import json
import os

import croniter
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyrogram import Client, filters
from pyrogram.types import Message

from api.alist.alist_api import alist
from api.alist.base.base import AListAPIResponse
from config.config import bot_cfg, DOWNLOADS_PATH
from tools.filters import is_admin
from tools.scheduler_manager import aps
from tools.utils import parse_cron


# Backup alist configuration
async def backup_config():
    bc_dic = {
        "encrypted": "",
        "settings": await alist.setting_list(),
        "users": await alist.user_list(),
        "storages": await alist.storage_list(),
        "metas": await alist.meta_list(),
    }
    for k, v in bc_dic.items():
        if isinstance(v, AListAPIResponse):
            bc_dic[k] = (
                v.raw_data.get("content")
                if isinstance(v.raw_data, dict)
                else v.raw_data
            )

    data = json.dumps(bc_dic, indent=4, ensure_ascii=False)  # Format JSON
    now = datetime.datetime.now()
    current_time = now.strftime("%Y_%m_%d_%H_%M_%S")  # Get current time
    bc_file_name = DOWNLOADS_PATH.joinpath(f"alist_backup_{current_time}.json")
    with open(bc_file_name, "w", encoding="utf-8") as b:
        b.write(data)
    return bc_file_name


# Listen for reply messages
@Client.on_message(
    (filters.text & filters.reply & filters.private) & ~filters.regex("^/") & is_admin
)
async def echo_bot(_, message: Message):
    if message.reply_to_message.document:  # Check if the replied message contains a file
        await message.delete()
        await message.reply_to_message.edit_caption(
            caption=f"#Alist Configuration Backup\n{message.text}",
        )


# Send backup file
@Client.on_message(filters.command("bc") & filters.private & is_admin)
async def send_backup_file(_, message: Message):
    bc_file_name = await backup_config()
    await message.reply_document(document=bc_file_name, caption="#Alist Configuration Backup")
    os.remove(bc_file_name)


# Scheduled task — send backup file
async def recovery_send_backup_file(cli: Client):
    bc_file_name = await backup_config()
    await cli.send_document(
        chat_id=bot_cfg.admin, document=bc_file_name, caption="#Alist Scheduled Backup"
    )
    os.remove(bc_file_name)
    logger.info("Scheduled backup successful")


def start_timed_backup(app):
    if bot_cfg.backup_time != "0":
        aps.add_job(
            func=recovery_send_backup_file,
            args=[app],
            trigger=CronTrigger.from_crontab(bot_cfg.backup_time),
            job_id="send_backup_messages_regularly_id",
        )
        logger.info("Scheduled backup started")


# Set backup time & enable scheduled backup
@Client.on_message(filters.command("sbt") & filters.private & is_admin)
async def set_backup_time(cli: Client, message: Message):
    mtime = " ".join(message.command[1:])
    if len(mtime.split()) == 5:
        bot_cfg.backup_time = mtime
        cron = croniter.croniter(bot_cfg.backup_time, datetime.datetime.now())
        next_run_time = cron.get_next(datetime.datetime)  # Next backup time
        if aps.job_exists("send_backup_messages_regularly_id"):
            aps.modify_job(
                job_id="send_backup_messages_regularly_id",
                trigger=CronTrigger.from_crontab(bot_cfg.backup_time),
            )
            text = f"Modified successfully!\nNext backup time: {next_run_time}"
        else:
            aps.add_job(
                func=recovery_send_backup_file,
                trigger=CronTrigger.from_crontab(bot_cfg.backup_time),
                job_id="send_backup_messages_regularly_id",
                args=[cli],
            )
            text = f"Scheduled backup enabled!\nNext backup time: {next_run_time}"
        await message.reply(text)
    elif mtime == "0":
        bot_cfg.backup_time = mtime
        aps.pause_job("send_backup_messages_regularly_id")
        await message.reply("Scheduled backup disabled")
    elif not mtime:
        text = f"""
Format: /sbt + 5-field cron expression, use 0 to disable
Next backup time: `{parse_cron(bot_cfg.backup_time) if bot_cfg.backup_time != '0' else 'Disabled'}`

Examples:
<code>/sbt 0</code> Disable scheduled backup
<code>/sbt 0 8 * * *</code> Run daily at 8 AM
<code>/sbt 30 20 */3 * *</code> Run every 3 days at 8:30 PM

 5-field cron expression format explanation
  ——Minute (0 - 59)
 |  ——Hour (0 - 23)
 | |  ——Day (1 - 31)
 | | |  ——Month (1 - 12)
 | | | |  ——Weekday (0 - 6, 0 is Monday)
 | | | | |
 * * * * *

"""
        await message.reply(text)
    else:
        await message.reply("Invalid format")
