# -*- coding: UTF-8 -*-
import asyncio

import httpx
import pyrogram
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from loguru import logger
from pyrogram import Client, filters
from pyrogram.types import BotCommand, Message

from api.alist.alist_api import alist
from config.config import bot_cfg, plb_cfg
from tools.filters import is_admin

logger.add("logs/bot.log", rotation="5 MB")

scheduler = AsyncIOScheduler()

proxy = {
    "scheme": bot_cfg.scheme,  # Supports "socks4", "socks5", and "http"
    "hostname": bot_cfg.hostname,
    "port": bot_cfg.port,
}

plugins = dict(root="module")
app = Client(
    "my_bot",
    proxy=proxy if all(proxy.values()) else None,
    bot_token=bot_cfg.bot_token,
    api_id=bot_cfg.api_id,
    api_hash=bot_cfg.api_hash,
    plugins=plugins,
    lang_code="en",
)


# Set menu
@app.on_message(filters.command("menu") & filters.private & is_admin)
async def menu(_, message: Message):
    # Visible to administrators in private chat
    admin_cmd = {
        "s": "Search for files",
        "roll": "Random recommendations",
        "sl": "Set the number of search results",
        "zl": "Turn on/off direct links",
        "dt": "Set timed deletion of search results",
        "st": "Storage management",
        "sf": "Cloudflare node management",
        "vb": "View download node information",
        "bc": "Backup Alist configuration",
        "sbt": "Set scheduled backup",
        "sr": "Random recommendation settings",
        "od": "Offline download",
        "help": "View help",
    }
    # Visible to all users
    user_cmd = {
        "s": "Search file",
        "roll": "Random recommendation",
        "vb": "View download node information",
    }
    admin_cmd = [BotCommand(k, v) for k, v in admin_cmd.items()]
    user_cmd = [BotCommand(k, v) for k, v in user_cmd.items()]

    await app.delete_bot_commands()
    await app.set_bot_commands(
        admin_cmd, scope=pyrogram.types.BotCommandScopeChat(chat_id=bot_cfg.admin)
    )
    await app.set_bot_commands(user_cmd)
    await message.reply("The menu has been set successfully. Please exit the chat interface and re-enter to refresh the menu.")


# Bot startup verification
def checking():
    try:
        app.loop.run_until_complete(alist.storage_list())
    except httpx.HTTPStatusError:
        logger.error("Failed to connect to Alist, please check whether the configuration alist_host is filled in correctly")
        exit()
    except httpx.ReadTimeout:
        logger.error("Connection to Alist timed out, please check the website status")
        exit()
    return logger.info("Bot starts running...")


fast = FastAPI()


def run_fastapi():
    async def _start():
        c = uvicorn.Config(
            "bot:fast", port=plb_cfg.port, log_level="error", host="0.0.0.0"
        )
        server = uvicorn.Server(c)
        await server.serve()

    if plb_cfg.enable:
        names = [task.get_name() for task in asyncio.all_tasks(app.loop)]
        if "fastapi" not in names:
            app.loop.create_task(_start(), name="fastapi")
        logger.info(f"Proxy load balancing has started | http://127.0.0.1:{plb_cfg.port}")


if __name__ == "__main__":
    checking()
    from module.init import init_task

    init_task(app)
    run_fastapi()
    app.run()
