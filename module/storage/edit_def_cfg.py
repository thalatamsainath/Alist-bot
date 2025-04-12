import json

from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config.config import chat_data, st_cfg
from module.storage.storage import (
    st_storage_amend,
    text_dict,
)
from tools.filters import is_admin
from tools.utils import translate_key


# Cancel modifying default configuration
@Client.on_callback_query(filters.regex(r"^st_storage_cfg_off$"))
async def sst_storage_cfg_off_callback(_, __):
    chat_data["st_storage_cfg_amend"] = False
    await st_storage_amend("", "")


def _st_storage_cfg_amend_filter(_, __, ___):
    return bool(
        "st_storage_cfg_amend" in chat_data and chat_data["st_storage_cfg_amend"]
    )


st_storage_cfg_amend_filter = filters.create(_st_storage_cfg_amend_filter)


# Modify storage default configuration - button callback
@Client.on_callback_query(filters.regex(r"^st_storage_cfg_amend$"))
async def st_storage_amend_callback(_, __):
    chat_data["st_storage_cfg_amend"] = True
    t = translate_key(
        translate_key(st_cfg.storage, text_dict["common"]),
        text_dict["additional"],
    )
    t = json.dumps(t, indent=4, ensure_ascii=False)
    button = [
        [InlineKeyboardButton("❌Cancel Modification", callback_data="st_storage_cfg_off")],
        [InlineKeyboardButton("↩️Return to Storage Management", callback_data="re_st_menu")],
    ]
    text = f"""Current Configuration:
<code>{t}</code>

Supported Options: <a href="https://telegra.ph/驱动字典-03-20">Click to View</a>
First copy the current configuration, modify it, and then send it back.

Format (Json):
1. Add 4 spaces at the beginning of each line.
2. Add a comma "," at the end of each line except the last one.

"""
    await chat_data["storage_menu_button"].edit(
        text=text,
        reply_markup=InlineKeyboardMarkup(button),
        disable_web_page_preview=True,
    )


# Modify default storage configuration
@Client.on_message(
    filters.text & filters.private & st_storage_cfg_amend_filter & is_admin
)
async def st_storage_cfg_amend(_, message: Message):
    message_text = message.text
    await message.delete()
    button = [
        [InlineKeyboardButton("🔄Modify Again", callback_data="st_storage_cfg_amend")],
        [InlineKeyboardButton("↩️Return to Storage Management", callback_data="re_st_menu")],
    ]
    try:
        message_text = json.loads(message_text)
    except json.decoder.JSONDecodeError as z:
        await chat_data["storage_menu_button"].edit(
            text=f"Configuration Error\n——————————\nPlease check the configuration:\n<code>{message_text}</code>\n{z}",
            reply_markup=InlineKeyboardMarkup(button),
        )
    else:
        new_dict = {
            v: k for k, v in text_dict["common"].items()
        }  # Swap keys and values in the common dictionary
        new_add_dict = {
            v: k for k, v in text_dict["additional"].items()
        }  # Swap keys and values in the additional dictionary
        new_dict |= new_add_dict
        t = translate_key(message_text, new_dict)
        st_cfg.storage = t
        await st_storage_amend("", "")

    chat_data["st_storage_cfg_amend"] = False
    chat_data["chat_id"] = message.chat.id
    chat_data["message_id"] = message.id
