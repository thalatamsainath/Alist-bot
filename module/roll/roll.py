# -*- coding: UTF-8 -*-
import json
import os
import random
import urllib.parse

from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from api.alist.alist_api import alist
from config.config import chat_data, roll_cfg, bot_cfg
from module.roll.random_kaomoji import random_kaomoji
from tools.filters import is_admin
from tools.utils import pybyte

return_button = [
    InlineKeyboardButton("↩️Return to Menu", callback_data="sr_return"),
    InlineKeyboardButton("❌Close Menu", callback_data="sr_close"),
]


def btn():
    return [
        [
            InlineKeyboardButton("🛠Modify Configuration", callback_data="edit_roll"),
            InlineKeyboardButton(
                "✅Random Recommendation" if roll_cfg.roll_disable else "❎Random Recommendation",
                callback_data="roll_off" if roll_cfg.roll_disable else "roll_on",
            ),
        ],
        [InlineKeyboardButton("❌Close Menu", callback_data="sr_close")],
    ]


# Random Recommendation Menu
@Client.on_message(filters.command("sr") & filters.private & is_admin)
async def sr_menu(_, message: Message):
    chat_data["sr_menu"] = await message.reply(
        text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn())
    )


# Random Recommendation
@Client.on_message(filters.command("roll"))
async def roll(_, message: Message):
    if bot_cfg.member and message.chat.id not in bot_cfg.member:
        return
    if not roll_cfg.roll_disable:
        return
    roll_str = " ".join(message.command[1:])
    if roll_str.replace("？", "?") == "?":
        t = "\n".join(list(roll_cfg.path.keys()))
        text = f"Added Keywords:\n<code>{t}</code>"
        return await message.reply(text)
    if roll_cfg.path:
        names, sizes, url = await generate(key=roll_str or "")
        text = f"""
{random_kaomoji()}：<a href="{url}">{names}</a>
{f'{random_kaomoji()}：{sizes}' if sizes != '0.0b' else ''}
"""
        await message.reply(text, disable_web_page_preview=True)
    else:
        await message.reply("Please add a path first")


# Menu Button Callback
@Client.on_callback_query(filters.regex("^sr_"))
async def menu(_, query: CallbackQuery):
    data = query.data
    if data == "sr_return":
        chat_data["edit_roll"] = False
        await chat_data["sr_menu"].edit(
            text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn())
        )
    elif data == "sr_close":
        chat_data["edit_roll"] = False
        await chat_data["sr_menu"].edit(text=random_kaomoji())


# Modify Configuration Button Callback
@Client.on_callback_query(filters.regex("edit_roll"))
async def edit_roll(_, query: CallbackQuery):
    j = json.dumps(roll_cfg.path, indent=4, ensure_ascii=False)
    text = (
        f"""
```json
{j}
```


Send after modification, format as JSON
A keyword can contain multiple paths, use list format
"""
        if j != "null"
        else """
```json
{
    "Keyword": "Path",
    "slg": "/slg",
    "gal": [
        "/gal",
        "/123"
    ]
}
```

Send after modification, format as JSON
A keyword can contain multiple paths, use list format
"""
    )
    await query.message.edit(
        text=text, reply_markup=InlineKeyboardMarkup([return_button])
    )
    chat_data["edit_roll"] = True


# Toggle Callback
@Client.on_callback_query(filters.regex("^roll_"))
async def roll_of(_, message):
    query = message.data
    roll_cfg.roll_disable = query != "roll_off"
    await chat_data["sr_menu"].edit(
        text=random_kaomoji(), reply_markup=InlineKeyboardMarkup(btn())
    )


def _edit_roll_filter(_, __, ___):
    return bool("edit_roll" in chat_data and chat_data["edit_roll"])


edit_roll_filter = filters.create(_edit_roll_filter)


# Write Configuration
@Client.on_message(filters.text & filters.private & edit_roll_filter & is_admin)
async def change_setting(_, message: Message):
    msg = message.text
    try:
        path = json.loads(msg)
    except Exception as e:
        await message.reply(text=f"Error: {str(e)}\n\nPlease modify and resend")
    else:
        await message.delete()
        chat_data["edit_roll"] = False
        roll_cfg.path = path
        await chat_data["sr_menu"].edit(
            text="Modification Successful", reply_markup=InlineKeyboardMarkup(btn())
        )


async def generate(key=""):
    # Use os.urandom to generate random bytes as seed
    random.seed(os.urandom(32))

    values_list = list(roll_cfg.path.values()) if key == "" else roll_cfg.path[key]
    r_path = get_random_value(values_list)
    data = await alist.fs_list(r_path)
    content = data.data["content"]

    selected_item = random.choice(content)
    name = selected_item["name"]
    size = selected_item["size"]
    get_path = f"{r_path}/{name}"

    url = bot_cfg.alist_web + get_path
    url = urllib.parse.quote(url, safe=":/")
    return name, pybyte(size), url


# Recursive List, Return Random Value
def get_random_value(data):
    if not isinstance(data, list):
        return data
    random_value = random.choice(data)
    return (
        get_random_value(random_value)
        if isinstance(random_value, list)
        else random_value
    )
