import json
from typing import Union

from loguru import logger
from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from api.alist.alist_api import alist
from config.config import chat_data
from module.storage.storage import (
    st_return,
    ns_button_list,
    text_dict,
    return_button,
    ns_mode_b_delete,
    ns_re_list_mode_b,
    remove_quotes,
    storage_config,
    user_cfg,
)
from tools.filters import is_admin
from tools.utils import translate_key


def _ns_a_filter(_, __, ___):
    return bool("ns_a" in chat_data and chat_data["ns_a"])


ns_a_filter = filters.create(_ns_a_filter)


def _ns_b_filter(_, __, ___):
    return bool("ns_b" in chat_data and chat_data["ns_b"])


ns_b_filter = filters.create(_ns_b_filter)


# Add single storage and return to storage management menu
@Client.on_callback_query(filters.regex("^ns_re_menu$"))
async def ns_re_menu_callback(client: Client, __):
    await ns_mode_a_delete(client)
    await st_return()


# Add single storage and return to storage management menu
@Client.on_callback_query(filters.regex("^ns_re_new_b_menu$"))
async def ns_re_new_b_menu_callback(client: Client, __):
    await ns_mode_b_delete(client)
    await st_return()


# Return to the list of addable storages
@Client.on_callback_query(filters.regex("^ns_re_list$"))
async def ns_re_list_callback(_, __):
    chat_data["ns_a"] = False
    await ns(_, __)


# Return to the list of addable storages
@Client.on_callback_query(filters.regex("^ns_re_list_mode_b$"))
async def ns_re_list_mode_b_callback(client: Client, _):
    chat_data["ns_b"] = False
    await ns_re_list_mode_b(client)
    await ns(_, _)


# Send the list of addable storages
@Client.on_callback_query(filters.regex(r"^st_ns$"))
async def ns(_, __):
    r = await alist.driver_list()
    stj_key = list(r.data.keys())
    ns_storage_list = translate_key(stj_key, text_dict["driver"])  # Supported storage list for adding
    ns_button_list.clear()

    for storage_list_js in range(len(ns_storage_list)):
        button_ns = [
            InlineKeyboardButton(
                ns_storage_list[storage_list_js],
                callback_data=f"ns{str(stj_key[storage_list_js])}",
            )
        ]
        ns_button_list.append(button_ns)

    ns_button_list.insert(0, return_button)  # Add return and close menu buttons at the beginning of the list
    ns_button_list.append(return_button)  # Add return and close menu buttons at the end of the list

    await chat_data["storage_menu_button"].edit(
        text="Supported storages for adding:", reply_markup=InlineKeyboardMarkup(ns_button_list)
    )


# After selecting storage, send the add mode buttons
@Client.on_callback_query(filters.regex("^ns[^_]"))
async def ns_mode(_, query: CallbackQuery):  # Supported storage list for adding
    bvj = str(query.data.lstrip("ns"))  # Send selection mode menu
    global name
    # stj_key = list(json.loads(get_driver().text)['data'].keys())
    name = bvj
    button = [
        [
            InlineKeyboardButton("☝️Add Single", callback_data=f"ns_a{bvj}"),
            InlineKeyboardButton("🖐Add Multiple", callback_data=f"ns_b{bvj}"),
        ],
        [InlineKeyboardButton("↩️Return to Storage List", callback_data="ns_re_list")],
    ]
    await chat_data["storage_menu_button"].edit(
        text=f"<b>Selected Storage: {name}</b>\nChoose Mode:",
        reply_markup=InlineKeyboardMarkup(button),
    )


# Single mode, send template and listen for the next message
@Client.on_callback_query(filters.regex("ns_a"))
async def ns_mode_a(_, __):
    chat_data["ns_a"] = True
    text, common_dict_json = await storage_config(name)
    await chat_data["storage_menu_button"].edit(
        text=f"""<b>Selected Storage: {name}</b>\n```Storage Configuration\n{text}```\n*Required fields, default values can be omitted\nPlease modify the configuration and send""",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩️Return to Storage List", callback_data="ns_re_list")]]
        ),
    )


# Retry adding single storage after failure
@Client.on_callback_query(filters.regex("^ns_re_ns_mode_a$"))
async def ns_re_ns_mode_a_callback(client: Client, __):
    chat_data["ns_a"] = True
    await ns_mode_a_delete(client)


# Delete user and bot messages
async def ns_mode_a_delete(client: Client):
    await client.delete_messages(
        chat_id=chat_data["chat_id_a"], message_ids=chat_data["message_id_a"]
    )
    await client.delete_messages(
        chat_id=chat_data["chat_id"], message_ids=chat_data["message_id"]
    )


# Multiple mode, send template and listen for the next message
@Client.on_callback_query(filters.regex("ns_b"))
async def ns_mode_b(_, query: CallbackQuery):
    ns_new_b_list.clear()
    message_text_list.clear()
    chat_data["ns_b"] = True
    text = (await storage_config(name))[0]
    await chat_data["storage_menu_button"].edit(
        f"<b>Selected Storage: {name}</b>\n```Storage Configuration\n{text}```\n*Required fields, default values can be omitted\nPlease modify the configuration and send",
    )
    ns_mode_b_message_2 = await query.message.reply(
        text="Please send the storage configuration, ensure the mount path is not duplicated",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("↩️Return to Storage List", callback_data="ns_re_list_mode_b")]]
        ),
    )

    chat_data["ns_mode_b_message_2_chat_id"] = ns_mode_b_message_2.chat.id
    chat_data["ns_mode_b_message_2_message_id"] = ns_mode_b_message_2.id


# Create new storage in single mode
@Client.on_message(filters.text & filters.private & ns_a_filter & is_admin)
async def ns_new_a(_, message: Message):
    message_tj = await message.reply("Creating new storage...")
    chat_data["chat_id_a"] = message_tj.chat.id
    chat_data["message_id_a"] = message_tj.id
    message_text = message.text
    st_cfg, user_cfg_code = await user_cfg(message_text)  # Parse user-sent storage configuration
    if user_cfg_code != 200:
        text = f"""Addition failed!
——————————
Please check the configuration and resend:
<code>{message_text}</code>

Error Key:
<code>{str(user_cfg_code)}</code>
"""
        await message_tj.edit(
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄Retry Adding", callback_data="ns_re_ns_mode_a"
                        )
                    ],
                    [InlineKeyboardButton("↩️︎Return to Storage Management", callback_data="ns_re_menu")],
                ]
            ),
        )
    else:
        ns_json = await alist.storage_create(remove_quotes(st_cfg))  # Create new storage
        if ns_json.code == 200:
            await message_tj.edit(
                text=f"{name} added successfully!",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "↩️Return to Storage Management", callback_data="ns_re_menu"
                            )
                        ]
                    ]
                ),
            )
        elif ns_json.code == 500:
            storage_id = str(ns_json.data["id"])
            st_info = await alist.storage_get(storage_id)  # Query specific storage information
            ns_up_json = await alist.storage_update(st_info.data)  # Update storage

            if ns_up_json.code == 200:
                await message_tj.edit(
                    text=f"{name} added successfully!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "↩️Return to Storage Management", callback_data="ns_re_menu"
                                )
                            ]
                        ]
                    ),
                )
            else:
                await message_tj.edit(
                    text=name + " addition failed!\n——————————\n" + ns_up_json["message"],
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "↩️Return to Storage Management", callback_data="ns_re_menu"
                                )
                            ]
                        ]
                    ),
                )
        else:
            await message_tj.edit(
                text=name + " addition failed!\n——————————\n" + ns_json["message"],
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "↩️Return to Storage Management", callback_data="ns_re_menu"
                            )
                        ]
                    ]
                ),
            )

    chat_data["ns_a"] = False
    chat_data["chat_id"] = message.chat.id
    chat_data["message_id"] = message.id


# Create new storage in batch mode, process user-sent configurations
ns_new_b_list = []  # Parsed configurations
message_text_list = []  # User-sent configurations
ns_new_b_message_id = {}  # Store message id and content


@Client.on_message(filters.text & filters.private & ns_b_filter & is_admin)
async def ns_new_b(client: Client, message: Message):
    message_text = message.text
    await storage_config(name)
    st_cfg, user_cfg_code = await user_cfg(message_text)  # Parse user-sent storage configuration

    ns_new_b_message_id.clear()

    a = json.dumps(st_cfg)
    b = json.loads(a)

    if user_cfg_code == 200:
        ns_new_b_list.append(b)
        message_text_list.append(message_text)  # Add user-sent configuration to the list

        # Delete user-sent message
        await message.delete()

        # Start processing the sent configuration
        await ns_r(client, message)
    else:
        message_text_list.append(
            f"Addition failed!\n——————————\nPlease check the configuration and resend:\n{message_text}\n\nError Key:\n{str(user_cfg_code)}"
        )
        text = ""
        for i in range(len(message_text_list)):
            textt = f"{i + 1}、\n<code>{str(message_text_list[i])}</code>\n\n"
            text += textt
        await message.delete()
        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=chat_data["ns_mode_b_message_2_message_id"],
                text=f"Added configurations:\n{str(text)}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "↩️Return to Storage List", callback_data="ns_re_list_mode_b"
                            )
                        ]
                    ]
                ),
            )
        except Exception as e:
            logger.info(e)
        message_text_list.pop()

    chat_data["chat_id"] = message.chat.id
    chat_data["message_id"] = message.id

    return


# Revoke added configuration
@Client.on_callback_query(filters.regex("^ns_re$"))
async def ns_remove(client: Client, query: CallbackQuery):
    message_text_list.pop()
    ns_new_b_list.pop()
    await ns_r(client, query)


# Refresh added storages
async def ns_r(client: Client, message: Union[Message, CallbackQuery]):
    text = ""
    for i in range(len(ns_new_b_list)):
        textt = f"{i + 1}、\n<code>{str(message_text_list[i])}</code>\n\n"
        text += textt
    button = [
        [
            InlineKeyboardButton("🔄Revoke", callback_data="ns_re"),
            InlineKeyboardButton("↩️Return", callback_data="ns_re_list_mode_b"),
        ],
        [InlineKeyboardButton("🎉Start Creating", callback_data="ns_sp")],
    ]
    ns_r_text = await client.edit_message_text(
        chat_id=(
            message.chat.id if isinstance(message, Message) else message.message.chat.id
        ),
        message_id=chat_data["ns_mode_b_message_2_message_id"],
        text="Added configurations:\n" + str(text),
        reply_markup=InlineKeyboardMarkup(button),
    )
    ns_new_b_message_id["text"] = ns_r_text.text


# Start batch creation of storages
@Client.on_callback_query(filters.regex("^ns_sp$"))
async def ns_new_b_start(client: Client, query: CallbackQuery):
    chat_data["ns_b"] = False
    message_b = []
    await client.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=chat_data["ns_mode_b_message_2_message_id"],
        text=f'<code>{ns_new_b_message_id["text"]}</code>',
    )
    ns_b_message_tj = await query.message.reply("Starting to add storages")
    text = ""
    for i in range(len(ns_new_b_list)):
        st_cfg = ns_new_b_list[i]
        ns_body = remove_quotes(st_cfg)
        ns_json = await alist.storage_create(ns_body)  # Create new storage
        mount_path = ns_new_b_list[i]["mount_path"]
        if ns_json.code == 200:
            message_b.append(f"`{mount_path}` | Added successfully!")
        elif (
            ns_json.code == 500 and "but storage is already created" in ns_json.message
        ):  # Initialization failed, but storage already created
            storage_id = str(ns_json.data["id"])
            st_info = await alist.storage_get(storage_id)  # Query specific storage information
            ns_up_json = await alist.storage_update(st_info.data)  # Update storage
            if ns_up_json.code == 200:
                message_b.append(f"`{mount_path}` | Added successfully!")
            else:
                message_b.append(
                    f"{mount_path} addition failed!\n——————————\n{ns_up_json}\n——————————"
                )
        elif (
            ns_json.code == 500 and "1062 (23000)" in ns_json.message
        ):  # Storage path already exists
            message_b.append(
                f"{mount_path} addition failed!\n——————————\n{ns_json.message}\n——————————"
            )
        else:
            message_b.append(
                f"{mount_path} addition failed!\n——————————\n{ns_json.message}\n——————————"
            )
        textt = f"{message_b[i]}\n"
        text += textt
        ns_new_bb_start = await ns_b_message_tj.edit(
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↩️︎Return to Storage Management", callback_data="ns_re_new_b_menu"
                        )
                    ]
                ]
            ),
        )
        chat_data["ns_new_b_start_chat_id"] = ns_new_bb_start.chat.id
        chat_data["ns_new_b_start_message_id"] = ns_new_bb_start.id

    ns_new_b_list.clear()
    message_text_list.clear()
