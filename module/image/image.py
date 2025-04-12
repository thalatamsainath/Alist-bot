# -*- coding: UTF-8 -*-
import asyncio
import datetime
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

from pyrogram import filters, Client
from pyrogram.types import Message

from api.alist.alist_api import alist
from config.config import img_cfg, DOWNLOADS_PATH, bot_cfg
from tools.filters import is_admin

# 4 threads
thread_pool = ThreadPoolExecutor(max_workers=4)


async def download_upload(message: Message):
    now = datetime.datetime.now()
    current_time = now.strftime("%Y_%m_%d_%H_%M_%S")  # Get current time
    file_name = f"{current_time}_{random.randint(1, 1000)}"
    # Generate file name
    if message.photo:  # Compressed sent image
        file_name = f"{file_name}.jpg"  # Compressed image defaults to .jpg

    elif message.document.mime_type.startswith("image/"):  # Uncompressed image file
        ext = os.path.splitext(message.document.file_name)[1]  # Get file extension
        file_name = f"{file_name}{ext}"

    # Local path + file name
    file_name_path = DOWNLOADS_PATH.joinpath(file_name)

    # Download image
    time.sleep(random.uniform(0.01, 0.2))
    msg = await message.reply_text(
        text="📥Downloading image...", quote=True, disable_web_page_preview=False
    )
    await message.download(file_name=file_name_path)
    # Upload to alist
    await msg.edit(text="📤Uploading image...", disable_web_page_preview=False)
    time.sleep(random.uniform(0.01, 0.2))
    await alist.upload(file_name_path, img_cfg.image_upload_path, file_name)

    # Delete image
    os.remove(file_name_path)

    # Refresh list
    await msg.edit(text="🔄Refreshing list...", disable_web_page_preview=False)
    time.sleep(random.uniform(0.01, 0.2))
    await alist.fs_list(img_cfg.image_upload_path, 1)
    # Get file information
    await msg.edit(text="⏳Getting link...", disable_web_page_preview=False)
    time.sleep(random.uniform(0.01, 0.2))
    get_url = await alist.fs_get(f"{img_cfg.image_upload_path}/{file_name}")
    image_url = get_url.data.raw_url  # Direct link

    text = f"""
Image Name: <code>{file_name}</code>
Image Link: <a href="{bot_cfg.alist_web}/{img_cfg.image_upload_path}/{file_name}">Open Image</a>
Direct Image Link: <a href="{image_url}">Download Image</a>
Markdown:
`![{file_name}]({image_url})`
"""
    # HTML:
    # <code>&lt;img src="{image_url}" alt="{file_name}" /&gt;</code>

    await msg.edit(text=text, disable_web_page_preview=True)


@Client.on_message((filters.photo | filters.document) & filters.private & is_admin)
async def single_mode(_, message: Message):
    # Check if a description is added
    if caption := message.caption:
        img_cfg.image_upload_path = None if caption == "Close" else str(caption)
    # Start running
    if img_cfg.image_upload_path:
        # Add task to thread pool
        # await download_upload(message)
        thread_pool.submit(asyncio.run, download_upload(message))
    else:
        text = """
Image hosting is not enabled. Please set an upload path to enable it.

First, select an image, then fill in the upload path in the "Add Description" field.
Format: `/image_hosting/test`
Enter `Close` to disable the image hosting feature.
The setting will be saved automatically, no need to set it every time.
"""
        await message.reply(text=text)
