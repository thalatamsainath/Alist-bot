# -*- coding: UTF-8 -*-
import argparse

import prettytable as pt
from pyrogram import filters, Client
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from api.alist.alist_api import alist
from api.alist.base.storage.get import StorageInfo
from config.config import bot_cfg, od_cfg
from tools.filters import is_admin
from tools.scheduler_manager import aps

# Download strategies
DOWNLOAD_STRATEGIES = {
    "delete_on_upload_succeed": "Delete after successful upload",
    "delete_on_upload_failed": "Delete on upload failure",
    "delete_never": "Never delete",
    "delete_always": "Always delete",
}

storage_mount_path: list[StorageInfo] = []


# Get the next step
async def _next(client, message, previous_step):
    if previous_step is None:
        if od_cfg.download_tool is None:
            return await message.reply(
                text="Please select an offline download tool",
                reply_markup=InlineKeyboardMarkup(
                    await get_offline_download_tool("od_tool_")
                ),
            )
        else:
            return await _next(client, message, "show_tool_menu")

    if previous_step == "show_tool_menu":
        # Default path not set
        if od_cfg.download_path is None:
            return await message.reply(
                text="Please select a storage path",
                reply_markup=InlineKeyboardMarkup(
                    await get_offline_download_path("od_path_")
                ),
            )
        else:
            return await _next(client, message, "show_path_menu")

    if previous_step == "show_path_menu":
        # Default strategy not set
        if od_cfg.download_strategy is None:
            return await message.reply(
                text="Please select a download strategy",
                reply_markup=InlineKeyboardMarkup(
                    get_offline_download_strategies("od_strategy_")
                ),
            )
        else:
            return await _next(client, message, "show_strategy_menu")

    if previous_step == "show_strategy_menu":
        res = await alist.add_offline_download(
            urls=od_cfg.download_url,
            tool=od_cfg.download_tool,
            path=od_cfg.download_path,
            delete_policy=od_cfg.download_strategy,
        )

        if res.code != 200:
            return await message.reply(
                text=f"❌Failed to create offline task, reason:\n{res['message']}"
            )

        content = ["**🎉Offline task created successfully**"]

        content.extend(f"Resource URL: {url}" for url in od_cfg.download_url)
        content.extend(
            (
                f"Download tool: {od_cfg.download_tool}",
                f"Storage path: `{od_cfg.download_path}`",
                f"Download strategy: `{od_cfg.download_strategy}`",
            )
        )
        await message.reply(text="\n".join(content))

        job_id = "offline_download_progress_notify"

        return aps.add_job(
            func=progress_notify,
            args=[client, job_id],
            trigger="interval",
            seconds=5,
            job_id=job_id,
        )


# Download progress notification
async def progress_notify(client: Client, job_id: str):
    undone_resp = await alist.get_offline_download_undone_task()
    done_resp = await alist.get_offline_download_done_task()

    if len(undone_resp.data) == 0:
        aps.remove_job(job_id)

    if len(done_resp.data) > 0:
        await send_message(client, done_resp.data)
        await alist.clear_offline_download_done_task()


# Send message
async def send_message(client, tasks):
    table = pt.PrettyTable(["File", "Task", "Status", "Reason"])
    table.align["File"] = "l"
    table.valign["Task"] = "m"
    table.valign["Status"] = "m"
    table.valign["Reason"] = "m"

    table._max_width = {"File": 9, "Task": 8, "Status": 7, "Reason": 6}

    for task in tasks:
        table.add_row(
            [
                task["name"].split(" ")[1],
                "Download",
                "Success" if task["state"] == 2 else "Failed",
                task["error"] if task["state"] != 2 else "-",
            ],
            divider=True,
        )

    await client.send_message(
        chat_id=bot_cfg.admin,
        disable_web_page_preview=True,
        text=f"<pre>{table}</pre>"[:4096],
        parse_mode=ParseMode.HTML,
    )


# Get bottom buttons
def get_bottom_buttons(prefix, should_have_return=True, should_have_close=True):
    buttons = []

    if should_have_return:
        buttons.append(InlineKeyboardButton("↩️Return", callback_data=f"{prefix}return"))

    if should_have_close:
        buttons.append(InlineKeyboardButton("❌Close", callback_data=f"{prefix}close"))

    return buttons


# Get offline download strategy buttons
def get_offline_download_strategies(prefix):
    buttons = [
        [
            InlineKeyboardButton(
                select_btn(value, key == od_cfg.download_strategy),
                callback_data=f"{prefix}{key}",
            )
        ]
        for key, value in DOWNLOAD_STRATEGIES.items()
    ]
    buttons.append(get_bottom_buttons(prefix))

    return buttons


# Parse command
def parse_command(commands):
    parser = argparse.ArgumentParser(description="Process input arguments.")

    parser.add_argument("urls", metavar="url", type=str, nargs="+", help="File download URLs")
    parser.add_argument(
        "--tool",
        "-t",
        dest="tool",
        type=str,
        nargs=1,
        default=argparse.SUPPRESS,
        help="Download tool",
    )
    parser.add_argument(
        "--path",
        "-p",
        dest="path",
        type=str,
        nargs=1,
        default=argparse.SUPPRESS,
        help="Storage path",
    )
    parser.add_argument(
        "--strategy",
        "-s",
        dest="strategy",
        type=str,
        nargs=1,
        default=argparse.SUPPRESS,
        help="Download strategy",
    )

    return parser.parse_args(commands)


# Offline download
@Client.on_message(filters.command("od") & filters.private & is_admin)
async def od_start(client: Client, message: Message):
    try:
        args = parse_command(message.command[1:])
    except (Exception, SystemExit):
        return await message.reply(
            text="Use the `/od` command followed by keywords to download to the corresponding storage.\nFor example:\n`/od url`\n`/od url url2`\n",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⚙️Modify default settings", callback_data="od_setting"
                        ),
                        InlineKeyboardButton(
                            "🔄Restore default settings", callback_data="od_restore"
                        ),
                    ]
                ]
            ),
        )
    od_cfg.download_url = args.urls

    await _next(client, message, previous_step=None)


# Menu button callback
@Client.on_callback_query(filters.regex("(return|close)$"))
async def bottom_menu_callback(_, query: CallbackQuery):
    # Go back when setting default items
    if [
        "od_update_tool_return",
        "od_update_path_return",
        "od_update_strategy_return",
    ].count(query.data) > 0:
        return await show_setting_menu(_, query)

    # Close
    if query.data.endswith("close"):
        return await query.message.delete()


# Offline download tool callback
@Client.on_callback_query(filters.regex("^od_tool_"))
async def tool_menu_callback(client: Client, query: CallbackQuery):
    od_cfg.download_tool = query.data.removeprefix("od_tool_")

    await _next(client, query.message, previous_step="show_tool_menu")


# Offline storage directory callback
@Client.on_callback_query(filters.regex("^od_path_"))
async def path_menu_callback(client: Client, query: CallbackQuery):
    od_cfg.download_path = storage_mount_path[
        int(query.data.removeprefix("od_path_"))
    ].mount_path

    await _next(client, query.message, previous_step="show_path_menu")


# Offline strategy callback
@Client.on_callback_query(filters.regex("^od_strategy_"))
async def strategy_menu_callback(client: Client, query: CallbackQuery):
    od_cfg.download_strategy = query.data.removeprefix("od_strategy_")

    await _next(client, message=query.message, previous_step="show_strategy_menu")


# Settings menu
@Client.on_callback_query(filters.regex("^od_setting"))
async def show_setting_menu(_, query: CallbackQuery):
    await query.message.edit(
        text="Please select the setting item to modify:",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Modify offline tool", callback_data="od_edit_tool")],
                [InlineKeyboardButton("Modify storage path", callback_data="od_edit_path")],
                [
                    InlineKeyboardButton(
                        "Modify download strategy", callback_data="od_edit_strategy"
                    )
                ],
                get_bottom_buttons("od_edit_", should_have_return=False),
            ]
        ),
    )


# Modify settings
@Client.on_callback_query(filters.regex("^od_edit_"))
async def show_setting_sub_menu(_, query: CallbackQuery):
    if query.data == "od_edit_tool":
        await query.message.edit(
            text="Current default offline tool: <b>"
            + (od_cfg.download_tool or "Not set")
            + "</b>\nYou can modify it to any of the following options",
            reply_markup=InlineKeyboardMarkup(
                await get_offline_download_tool("od_update_tool_")
            ),
        )
    elif query.data == "od_edit_path":
        await query.message.edit(
            text="Current default storage path: <b>"
            + (od_cfg.download_path or "Not set")
            + "</b>\nYou can modify it to any of the following options",
            reply_markup=InlineKeyboardMarkup(
                await get_offline_download_path("od_update_path_")
            ),
        )

    elif query.data == "od_edit_strategy":
        await query.message.edit(
            text="Current default download strategy: <b>"
            + (od_cfg.download_strategy or "Not set")
            + "</b>\nYou can modify it to any of the following options",
            reply_markup=InlineKeyboardMarkup(
                get_offline_download_strategies("od_update_strategy_")
            ),
        )


# Save settings
@Client.on_callback_query(filters.regex("^od_update_"))
async def update_setting(_, query: CallbackQuery):
    value = query.data
    if value.startswith("od_update_tool_"):
        od_cfg.download_tool = value.removeprefix("od_update_tool_")
        await query.message.edit_text(
            text="**⚙️Default offline tool set successfully**",
            reply_markup=InlineKeyboardMarkup(
                await get_offline_download_tool("od_update_tool_")
            ),
        )
    elif value.startswith("od_update_path_"):
        od_cfg.download_path = storage_mount_path[
            int(value.removeprefix("od_update_path_"))
        ].mount_path
        await query.message.edit_text(
            text="**⚙️Default storage path set successfully**",
            reply_markup=InlineKeyboardMarkup(
                await get_offline_download_path("od_update_path_")
            ),
        )
    elif value.startswith("od_update_strategy_"):
        od_cfg.download_strategy = value.removeprefix("od_update_strategy_")
        await query.message.edit_text(
            text="**⚙️Default download strategy set successfully**",
            reply_markup=InlineKeyboardMarkup(
                get_offline_download_strategies("od_update_strategy_")
            ),
        )


# Restore settings
@Client.on_callback_query(filters.regex("^od_restore"))
async def restore_setting(_, query: CallbackQuery):
    od_cfg.download_tool = None
    od_cfg.download_strategy = None
    od_cfg.download_path = None
    await query.message.edit(text="✅Offline download settings restored")


# Get storage and write to list
async def get_offline_download_path(prefix):
    st_info = (await alist.storage_list()).data

    storage_mount_path.clear()
    storage_mount_path.extend(st_info)

    buttons = [
        [
            InlineKeyboardButton(
                text=select_btn(
                    mp := storage_mount_path[index].mount_path,
                    mp == od_cfg.download_path,
                ),
                callback_data=prefix + str(index),
            )
        ]
        for index in range(len(storage_mount_path))
    ]
    buttons.append(get_bottom_buttons(prefix))

    return buttons


# Get offline download tools
async def get_offline_download_tool(prefix):
    response = await alist.get_offline_download_tools()  # Get offline download tool list

    response.data.sort()

    buttons = [
        [
            InlineKeyboardButton(
                select_btn(item, item == od_cfg.download_tool),
                callback_data=prefix + item,
            )
        ]
        for item in response.data
    ]
    buttons.append(get_bottom_buttons(prefix))

    return buttons


def select_btn(text: str, b: bool):
    return f"✅{text}" if b else text
