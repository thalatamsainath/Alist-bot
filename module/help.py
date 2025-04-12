from pyrogram import filters, Client
from pyrogram.types import Message

from tools.filters import is_admin, is_member


@Client.on_message(filters.command("start") & is_member)
async def start(_, message: Message):
    await message.reply("Send `/s+filename` to search")


@Client.on_message(filters.command("help") & filters.private & is_admin)
async def _help(_, message: Message):
    text = """
Send an image to test the image hosting feature.
"""
    await message.reply(text)
