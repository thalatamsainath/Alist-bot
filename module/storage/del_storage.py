from pyrogram import filters, Client
from pyrogram.types import (
    InlineKeyboardMarkup,
    CallbackQuery,
)

from api.alist.alist_api import alist
from config.config import chat_data
from module.storage.storage import get_storage, mount_path, driver_id, button_list


# Send the Delete Storage button list
@Client.on_callback_query(filters.regex(r"^st_ds$"))
async def ds(_, __):
    await get_storage(callback_data_pr="ds")
    await chat_data["storage_menu_button"].edit(
        text="Click to delete storage\nStorage list:", reply_markup=InlineKeyboardMarkup(button_list)
    )


# Delete storage
@Client.on_callback_query(filters.regex("^ds"))
async def ds_callback(_, query: CallbackQuery):
    bvj = int(query.data.strip("ds"))
    await alist.storage_delete(driver_id[bvj])
    st_id = mount_path[bvj]
    await get_storage(callback_data_pr="ds")
    await chat_data["storage_menu_button"].edit(
        text=f"🗑Deleted storage: `{st_id}`", reply_markup=InlineKeyboardMarkup(button_list)
    )
