import datetime
import re

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, CallbackQuery

from api.alist.alist_api import alist
from config.config import chat_data
from module.storage.storage import (
    get_storage,
    button_list,
    driver_id,
    mount_path,
)


# Send the Copy Storage button list
@Client.on_callback_query(filters.regex(r"^st_cs$"))
async def cs(_, __):
    await get_storage(callback_data_pr="cs")
    await chat_data["storage_menu_button"].edit(
        text="Click to copy storage\nStorage list:", reply_markup=InlineKeyboardMarkup(button_list)
    )


# Copy storage
@Client.on_callback_query(filters.regex("^cs"))
async def cs_callback(_, query: CallbackQuery):
    bvj = int(query.data.strip("cs"))
    storage_id = str(driver_id[bvj])
    st = (await alist.storage_get(storage_id)).data  # Get storage
    del st.id  # Delete storage ID
    now = datetime.datetime.now()
    current_time = now.strftime("%M%S")  # Get current time

    cs_mount_path = st.mount_path
    cs_order = st.order
    if ".balance" not in cs_mount_path:  # Modify the mount_path of the storage
        st.mount_path = f"{cs_mount_path}.balance{current_time}"
    else:
        cs_mount_path_text = re.sub(".balance.*", "", cs_mount_path)
        st.mount_path = f"{cs_mount_path_text}.balance{current_time}"
    st.order = cs_order + 1  # Increment the order based on the current configuration

    await alist.storage_create(st)  # Create new storage

    await get_storage(callback_data_pr="cs")
    await chat_data["storage_menu_button"].edit(
        text=f"Copied\n`{mount_path[bvj]}` -> `{st.mount_path}`",
        reply_markup=InlineKeyboardMarkup(button_list),
    )
