# -*- coding: UTF-8 -*-
import asyncio
import math
import urllib.parse

from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from api.alist.alist_api import alist
from api.alist.base import Content
from config.config import search_cfg, bot_cfg, DT
from tools.filters import is_admin, is_member
from tools.utils import pybyte, schedule_delete_messages

PAGE: dict[str, "Page"] = {}


class Page:
    def __init__(self, text: list[str] = None):
        self.index = 0
        self.text = text
        self.per_page = search_cfg.per_page
        self.page_count = math.ceil(len(text) / self.per_page)

    def now_page(self) -> str:
        i = self.index * self.per_page
        text = self.text[i : i + self.per_page]
        return "".join(text)

    def next_page(self) -> str:
        if self.index < self.page_count - 1:
            self.index += 1
        return self.now_page()

    def previous_page(self) -> str:
        if self.index > 0:
            self.index -= 1
        return self.now_page()

    @property
    def btn(self) -> list:
        return [
            [
                InlineKeyboardButton(
                    f"{self.index + 1}/{self.page_count}", callback_data="search_pages"
                )
            ],
            [
                InlineKeyboardButton("⬆️Previous Page", callback_data="search_previous_page"),
                InlineKeyboardButton("⬇️Next Page", callback_data="search_next_page"),
            ],
        ]


# Set items per page
@Client.on_message(filters.command("sl") & is_admin)
async def sl(_, msg: Message):
    sl_str = " ".join(msg.command[1:])
    if sl_str.isdigit():
        search_cfg.per_page = int(sl_str)
        await msg.reply(f"Modified: __{sl_str}__ items per page")
    else:
        await msg.reply("Example: `/sl 5`")


# Toggle direct links
@Client.on_message(filters.command("zl") & is_admin)
async def zl(_, msg: Message):
    z = search_cfg.z_url
    search_cfg.z_url = not z
    await msg.reply(f"{'Disabled' if z else 'Enabled'} direct links")


# Set timed delete duration
@Client.on_message(filters.command("dt") & is_admin)
async def timed_del(_, msg: Message):
    dt = " ".join(msg.command[1:])
    if msg.chat.type.value == "private":
        return await msg.reply("Please use this command in a group or channel")
    if dt.isdigit():
        if int(dt) == 0:
            search_cfg.timed_del = DT(msg.chat.id, 0)
            return await msg.reply("Timed delete disabled")
        search_cfg.timed_del = DT(msg.chat.id, int(dt))
        await msg.reply(f"Modified: Delete after __{dt}__ seconds")
    else:
        await msg.reply("Set the timed delete duration for search results. Use 0 to disable. Unit: seconds\nExample: `/dt 60`")


# Search
@Client.on_message(filters.command("s") & is_member)
async def s(cli: Client, message: Message):
    k = " ".join(message.command[1:])
    if not k:
        return await message.reply("Please include a file name, e.g., `/s chocolate`")
    msg = await message.reply("Searching...")

    result = await alist.search(k)
    if not (c := result.data.content):
        return await msg.edit("No files found. Try a different keyword.")

    text, button = await build_result(c, message)
    msg = await msg.edit(
        text=text,
        reply_markup=InlineKeyboardMarkup(button),
        disable_web_page_preview=True,
    )

    # Timed delete in groups or channels
    if (
        getattr(search_cfg.timed_del, "time", False)
        and message.chat.type.value != "private"
    ):
        await schedule_delete_messages(
            cli,
            message.chat.id,
            [message.id, msg.id],
            delay_seconds=search_cfg.timed_del.time,
        )


async def build_result(content: list[Content], message: Message) -> (str, list):
    """Build search result message"""
    task = [build_result_item(count, item) for count, item in enumerate(content)]
    text = list(await asyncio.gather(*task))

    cmid = f"{message.chat.id}|{message.id + 1}"
    page = Page(text)
    PAGE[cmid] = page
    text = page.now_page()
    return text, page.btn


async def build_result_item(count: int, item: Content) -> str:
    """Build search result message body"""
    file_name, path, file_size, folder = item.name, item.parent, item.size, item.is_dir

    # If not a folder and direct links are enabled, get the direct link
    dl = (
        f" | [Direct Download]({(await alist.fs_get(f'{path}/{file_name}')).data.raw_url})"
        if not folder and search_cfg.z_url
        else ""
    )

    fl = urllib.parse.quote(f"{bot_cfg.alist_web}{path}/{file_name}", safe=":/")
    file_type = "📁Folder" if folder else "📄File"

    return f"{count + 1}.{file_type}: `{file_name}`\n[🌐Open Website]({fl}){dl} | __{pybyte(file_size)}__\n\n"


# Pagination
@Client.on_callback_query(filters.regex(r"^search"))
async def search_button_callback(_, query: CallbackQuery):
    data, msg = query.data, query.message
    cmid = f"{msg.chat.id}|{msg.id}"
    page = PAGE.get(cmid)
    match data:
        case "search_next_page":
            text = page.next_page()
        case "search_previous_page":
            text = page.previous_page()
        case _:
            return
    try:
        await msg.edit(
            text,
            reply_markup=InlineKeyboardMarkup(page.btn),
            disable_web_page_preview=True,
        )
    except MessageNotModified:
        ...
