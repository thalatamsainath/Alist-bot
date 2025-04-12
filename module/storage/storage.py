# -*- coding: UTF-8 -*-
import asyncio
import json

from loguru import logger
from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from api.alist.alist_api import alist
from config.config import st_cfg, chat_data
from tools.filters import is_admin
from tools.utils import translate_key

mount_path = []  # Store paths
disabled = []  # Store whether disabled
driver_id = []  # Store IDs
ns_button_list = []  # Buttons for supported storage additions
button_list = []
common_dict = {}  # Template for new storage JSON

with open("module/storage/cn_dict.json", "r", encoding="utf-8") as c:
    text_dict = json.load(c)

#####################################################################################
#####################################################################################
# Return to menu
return_button = [
    InlineKeyboardButton("↩️Return to Storage Management", callback_data="re_st_menu"),
    InlineKeyboardButton("❌Close Menu", callback_data="st_close"),
]

st_button = [
    [InlineKeyboardButton("⬆️Auto Sort", callback_data="auto_sorting")],
    [
        InlineKeyboardButton("⏯Enable/Disable Storage", callback_data="st_vs"),
        InlineKeyboardButton("📋Copy Storage", callback_data="st_cs"),
    ],
    [
        InlineKeyboardButton("🆕New Storage", callback_data="st_ns"),
        InlineKeyboardButton("🗑️Delete Storage", callback_data="st_ds"),
    ],
    [
        InlineKeyboardButton("📋Copy Storage Config", callback_data="st_storage_copy_list"),
        InlineKeyboardButton("🛠️Modify Default Config", callback_data="st_storage_amend"),
    ],
    [InlineKeyboardButton("❌Close Menu", callback_data="st_close")],
]

vs_all_button = [
    InlineKeyboardButton("✅Enable All Storage", callback_data="vs_onall"),
    InlineKeyboardButton("❌Disable All Storage", callback_data="vs_offall"),
]


#####################################################################################
# Button callbacks
#####################################################################################
# Return to storage management menu
@Client.on_callback_query(filters.regex(r"^re_st_menu$"))
async def st_return_callback(_, __):
    chat_data["st_storage_cfg_amend"] = False
    await st_return()


# Close storage management menu
@Client.on_callback_query(filters.regex(r"^st_close$"))
async def st_close(_, __):
    await chat_data["storage_menu_button"].edit("Exited 'Storage Management'")


#####################################################################################
#####################################################################################


async def st_aaa():
    try:
        st_info_list = (await alist.storage_list()).data
    except Exception:
        text = "Connection to Alist timed out, please check the website status"
        logger.error(text)
        return text
    else:
        zcc = len(st_info_list)
        jysl = sum(bool(item.disabled) for item in st_info_list)
        qysl = zcc - jysl
        return f"Storage Count: {zcc}\nEnabled: {qysl}\nDisabled: {jysl}"


# Storage management menu
@Client.on_message(filters.command("st") & filters.private & is_admin)
async def st(_, message: Message):
    storage_menu_button = await message.reply(
        text=await st_aaa(), reply_markup=InlineKeyboardMarkup(st_button)
    )
    chat_data["storage_menu_button"]: Message = storage_menu_button


# Return to storage management menu
async def st_return():
    await chat_data["storage_menu_button"].edit(
        text=await st_aaa(), reply_markup=InlineKeyboardMarkup(st_button)
    )


# Modify default storage configuration
@Client.on_callback_query(filters.regex(r"^st_storage_amend$"))
async def st_storage_amend(_, __):
    t = translate_key(
        translate_key(st_cfg.storage, text_dict["common"]),
        text_dict["additional"],
    )
    t = json.dumps(t, indent=4, ensure_ascii=False)

    button = [
        [InlineKeyboardButton("🔧Modify Config", callback_data="st_storage_cfg_amend")],
        [InlineKeyboardButton("↩️Return to Storage Management", callback_data="re_st_menu")],
    ]

    await chat_data["storage_menu_button"].edit(
        text=f"Current Config:\n<code>{t}</code>", reply_markup=InlineKeyboardMarkup(button)
    )


#####################################################################################
#####################################################################################


# Auto sort
@Client.on_callback_query(filters.regex(r"auto_sorting"))
async def auto_sorting(_, query: CallbackQuery):
    st_list = (await alist.storage_list()).data
    st_list.sort(key=lambda x: x.mount_path)
    await query.message.edit_text("Sorting...")

    task = []
    for i, v in enumerate(st_list):
        v.order = i
        task.append(alist.storage_update(v))
    results = await asyncio.gather(*task, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Sorting failed: {result}")
    return await st_return()


# Delete user and bot information
async def ns_mode_b_delete(client: Client):
    await client.delete_messages(
        chat_id=chat_data["ns_new_b_start_chat_id"],
        message_ids=chat_data["ns_new_b_start_message_id"],
    )
    await client.delete_messages(
        chat_id=chat_data["ns_mode_b_message_2_chat_id"],
        message_ids=chat_data["ns_mode_b_message_2_message_id"],
    )


# Delete user and bot information
async def ns_re_list_mode_b(client: Client):
    await client.delete_messages(
        chat_id=chat_data["ns_mode_b_message_2_chat_id"],
        message_ids=chat_data["ns_mode_b_message_2_message_id"],
    )


#####################################################################################
#####################################################################################


# Parse user-sent storage configuration, return parsed configuration and status code
async def user_cfg(message_text):  # sourcery skip: dict-assign-update-to-union
    message_config = {"addition": {}}  # Parse user-sent configuration
    new_dict = {v: k for k, v in text_dict["common"].items()}  # Swap keys and values in common
    new_add_dict = {
        v: k for k, v in text_dict["additional"].items()
    }  # Swap keys and values in additional
    new_dict.update(new_add_dict)  # Merge swapped common and additional
    try:
        user_cfg_code = 200
        for i in message_text.split("\n"):
            k = i.split("=")[0].strip(" * ")
            l_i = new_dict.get(k, k)
            r_i = i.split("=")[1].replace(" ", "")
            if r_i == "True":
                r_i = "true"
            elif r_i == "False":
                r_i = "false"
            if l_i in text_dict["common"]:
                message_config[l_i] = r_i
            else:
                message_config["addition"][l_i] = r_i
    except (KeyError, IndexError) as e:
        user_cfg_code = e
    else:
        common_dict["addition"].update(message_config["addition"])
        message_config["addition"].update(common_dict["addition"])
        common_dict.update(message_config)  # Update default config with user-sent config
        common_dict["addition"] = f"""{json.dumps(common_dict['addition'])}"""
    return common_dict, user_cfg_code


# Get storage and write to list
async def get_storage(callback_data_pr):
    mount_path.clear()
    disabled.clear()
    driver_id.clear()
    button_list.clear()

    vs_data = (await alist.storage_list()).data  # Get storage list

    for item in vs_data:
        mount_path.append(item.mount_path)
        disabled.append(item.disabled)
        driver_id.append(item.id)

    for button_js in range(len(mount_path)):
        disabled_a = "❌" if disabled[button_js] else "✅"

        # Add storage button
        storage_button = [
            InlineKeyboardButton(
                disabled_a + mount_path[button_js],
                callback_data=callback_data_pr + str(button_js),
            )
        ]
        button_list.append(storage_button)

    if driver_id[7:]:
        button_list.insert(0, return_button)  # Add return and close menu buttons at the start
    button_list.append(return_button)  # Add return and close menu buttons at the end
    return button_list


# Remove quotes from numbers and booleans in JSON
def remove_quotes(obj):
    if isinstance(obj, (int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: remove_quotes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [remove_quotes(elem) for elem in obj]
    elif isinstance(obj, str):
        try:
            return int(obj)
        except ValueError:
            try:
                return float(obj)
            except ValueError:
                if obj.lower() == "true":
                    return True
                elif obj.lower() == "false":
                    return False
                else:
                    return obj
    else:
        return obj


# Parse driver configuration template and return new storage JSON template, message template
async def storage_config(driver_name):
    storage_name = driver_name
    additional_dict = {}
    default_storage_config = []  # Default storage configuration
    default_storage_config_message = []  # Template sent to user
    common_dict["driver"] = driver_name  # Add driver name to dictionary
    stj = (await alist.driver_list()).data

    def common_c(vl):
        for i in range(len(stj[storage_name][vl])):
            stj_name = stj[storage_name][vl][int(i)]["name"]  # Storage config name
            stj_bool = stj[storage_name][vl][int(i)]["type"]
            stj_default = (
                stj[storage_name][vl][int(i)]["default"]
                if stj_bool != "bool"
                else "false"
            )  # Storage config default value
            stj_options = stj[storage_name][vl][int(i)]["options"]  # Storage config options
            stj_required = stj[storage_name][vl][int(i)]["required"]  # Whether required
            cr = "*" if stj_required else ""
            co = f"({stj_options})" if stj_options else ""
            if vl == "common":
                common_dict[stj_name] = stj_default
            else:
                additional_dict[stj_name] = (
                    stj_default  # Add storage config name and default value to dictionary
                )
            sn = text_dict[vl].get(stj_name, stj_name)
            default_storage_config.append(f"{sn} = {stj_default}")
            storage = st_cfg.storage
            try:
                for k in storage.keys():
                    if k in text_dict["common"].keys():
                        common_dict[k] = storage[k]
                    else:
                        additional_dict[k] = storage[k]
            except (AttributeError, KeyError):
                ...
            if vl == "common":
                default_storage_config_message.append(
                    f"""{cr}{sn} = {common_dict[stj_name]} {co}"""
                )  # Template sent to user
            else:
                default_storage_config_message.append(
                    f"""{cr}{sn} = {additional_dict[stj_name]} {co}"""
                )  # Template sent to user

    common_c(vl="common")
    common_c(vl="additional")

    common_dict["addition"] = additional_dict  # Add additional to common
    common_dict_json = json.dumps(common_dict, ensure_ascii=False)
    default_storage_config_message = [
        f"{default_storage_config_message[i]}\n"
        for i in range(len(default_storage_config_message))
    ]
    text = "".join(default_storage_config_message)
    return text, common_dict_json
