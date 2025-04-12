import asyncio
import random

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from api.alist.alist_api import alist
from config.config import cf_cfg
from module.cloudflare.utile import re_remark
from tools.filters import step_filter
from tools.step_statu import step


@Client.on_callback_query(filters.regex("^random_node$"))
async def random_node_callback(_, cq: CallbackQuery):
    await cq.message.edit("Setting random proxy...")
    if e := await set_random_node():
        return await cq.message.edit(f"Failed to set: {e}")
    return await cq.message.edit("Stored random proxy | Completed!")


@Client.on_callback_query(filters.regex("^unified_node$"))
async def unified_node_callback(_, cq: CallbackQuery):
    await cq.message.edit("Please send the node address, including the protocol\nExample: `https://example.com`")
    step.set_step(cq.from_user.id, "unified_node", True)
    step.insert(cq.from_user.id, msg=cq.message)


@Client.on_message(filters.text & filters.private & step_filter("unified_node"))
async def set_unified_node(_, msg: Message):
    step.init(msg.from_user.id)
    m: Message = step.get(msg.from_user.id, "msg")
    m = await m.reply("Setting unified proxy...")
    if e := await set_random_node(msg.text):
        return await msg.reply(f"Failed to set: {e}")
    await m.edit("Stored unified proxy | Completed!")


async def set_random_node(node: str | None = None):
    """Set node proxy"""
    storage_list = await alist.storage_list()
    nodes = [f"https://{node.url}" for node in cf_cfg.nodes]
    for storage in storage_list.data:
        if storage.webdav_policy == "use_proxy_url" or storage.web_proxy:
            storage.down_proxy_url = node or random.choice(nodes)
            storage.remark = re_remark(storage.remark, storage.down_proxy_url)
    task = [alist.storage_update(s) for s in storage_list.data]
    results = await asyncio.gather(*task, return_exceptions=True)
    fail_results = [result for result in results if isinstance(result, Exception)]
    return fail_results
