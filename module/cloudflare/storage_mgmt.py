import asyncio
import random
from itertools import chain

from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyrogram import Client, filters
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup

from api.alist.alist_api import alist
from api.alist.base.storage.get import StorageInfo
from bot import run_fastapi
from config.config import bot_cfg, cf_cfg, chat_data, plb_cfg
from module.cloudflare.cloudflare import build_node_info, r_cf_menu
from module.cloudflare.utile import NodeStatus, check_node_status, re_remark
from tools.scheduler_manager import aps

_D = {
    "auto_switch_nodes": "Auto Switch Nodes",
    "status_push": "Node Status Push",
    "storage_mgmt": "Automatic Storage Management",
    "bandwidth_push": "Daily Bandwidth Statistics",
    "proxy_load_balance": "Proxy Load Balancing",
}


def switch(client: Client, enable: bool, option, job_id, mode):
    setattr(cf_cfg, option, enable)
    logger.info(f"{'Enabled' if enable else 'Disabled'}:{_D[option]}")

    job_functions = {
        "cronjob_bandwidth_push": send_cronjob_bandwidth_push,
        "cronjob_status_push": send_cronjob_status_push,
    }

    if (
        not any([cf_cfg.status_push, cf_cfg.storage_mgmt, cf_cfg.auto_switch_nodes])
        or option == "bandwidth_push"
    ):
        logger.info("Disabled: Node Monitoring")
        aps.pause_job(job_id)
    elif enable:
        aps.resume_job(job_id=job_id)
        args = (
            {"trigger": CronTrigger.from_crontab(cf_cfg.time)}
            if mode == 0
            else {"trigger": "interval", "seconds": 60}
        )
        aps.add_job(
            func=job_functions[job_id],
            args=[client],
            job_id=job_id,
            **args,
        )


async def toggle_auto_management(
    client: Client, cq: CallbackQuery, option, job_id, mode
):
    is_option_on = cq.data == f"{option}_on"
    switch(client, is_option_on, option, job_id, mode)
    await r_cf_menu(cq)


# Button callback for Node Status
@Client.on_callback_query(filters.regex("^status_push"))
async def status_push(cli: Client, cq: CallbackQuery):
    await toggle_auto_management(cli, cq, "status_push", "cronjob_status_push", 1)


# Button callback for Daily Bandwidth Statistics
@Client.on_callback_query(filters.regex("^bandwidth_push"))
async def bandwidth_push(cli: Client, cq: CallbackQuery):
    await toggle_auto_management(cli, cq, "bandwidth_push", "cronjob_bandwidth_push", 0)


# Button callback for Automatic Storage Management
@Client.on_callback_query(filters.regex("^storage_mgmt"))
async def storage_mgmt(cli: Client, cq: CallbackQuery):
    await toggle_auto_management(cli, cq, "storage_mgmt", "cronjob_status_push", 1)


# Button callback for Auto Switch Nodes
@Client.on_callback_query(filters.regex("^auto_switch_nodes"))
async def auto_switch_nodes(cli: Client, cq: CallbackQuery):
    await toggle_auto_management(cli, cq, "auto_switch_nodes", "cronjob_status_push", 1)


# Button callback for Proxy Load Balancing
@Client.on_callback_query(filters.regex("^proxy_load_balance"))
async def proxy_load_balance_switch(_, cq: CallbackQuery):
    plb_cfg.enable = not plb_cfg.enable
    if plb_cfg.enable:
        run_fastapi()
    logger.info(f"{'Enabled' if plb_cfg.enable else 'Disabled'}:Proxy Load Balancing")
    await r_cf_menu(cq)


# Bandwidth Notification Scheduled Task
async def send_cronjob_bandwidth_push(app):
    if cf_cfg.nodes:
        ni = await build_node_info(0)
        text = "Today's Bandwidth Statistics"
        for i in cf_cfg.chat_id:
            await app.send_message(
                chat_id=i,
                text=text,
                reply_markup=InlineKeyboardMarkup([ni.button_b, ni.button_c]),
            )


def start_bandwidth_push(app):
    if cf_cfg.bandwidth_push:
        aps.add_job(
            func=send_cronjob_bandwidth_push,
            args=[app],
            trigger=CronTrigger.from_crontab(cf_cfg.time),
            job_id="cronjob_bandwidth_push",
        )
        logger.info("Bandwidth Notification Started")


# Node Status Notification Scheduled Task
async def send_cronjob_status_push(app: Client):
    if not cf_cfg.nodes:
        return

    nodes = [value.url for value in cf_cfg.nodes]
    task = [check_node_status(node) for node in nodes]
    # All nodes
    results: list[NodeStatus] = [
        result
        for result in await asyncio.gather(*task, return_exceptions=True)
        if not isinstance(result, BaseException)
    ]
    # Available nodes
    available_nodes = await returns_the_available_nodes(results)

    task = [r_(node_status.url, node_status.status) for node_status in results]
    result = [i for i in await asyncio.gather(*task, return_exceptions=True) if i]

    tasks = [
        failed_node_management(app, node, status, available_nodes)
        for node, status in result
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    if flat_results := list(
        chain.from_iterable(result for result in results if result)
    ):
        text = "\n\n".join(flat_results)
        logger.info(text)
        await app.send_message(
            chat_id=bot_cfg.admin,
            text=text,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML,
        )


def start_status_push(app):
    if any([cf_cfg.status_push, cf_cfg.storage_mgmt, cf_cfg.auto_switch_nodes]):
        aps.add_job(
            func=send_cronjob_status_push,
            args=[app],
            trigger="interval",
            job_id="cronjob_status_push",
            seconds=60,
        )
        logger.info("Node Monitoring Started")


# Check all node statuses
async def r_(node: str, status_code: int):
    # First time fetching, default status is normal
    if not chat_data.get(node):
        chat_data[node] = 200
        chat_data[f"{node}_count"] = 0

    if status_code != 200:
        chat_data[f"{node}_count"] += 1

        # If errors are less than or equal to 3, do not proceed further
        if 0 < chat_data[f"{node}_count"] <= 3:
            return []
    return [node, status_code]


async def failed_node_management(
    app: Client, node, status_code, available_nodes
) -> list:
    # If the status code is the same as the last one, do not proceed
    if status_code == chat_data[node]:
        return []
    chat_data[node] = status_code
    chat_data[f"{node}_count"] = 0
    # Status notification
    await notify_status_change(app, node, status_code)

    # Automatic management
    try:
        st = (await alist.storage_list()).data
    except Exception:
        logger.error("Automatic storage management error: Failed to fetch storage list")
    else:
        task = [manage_storage(dc, node, status_code, available_nodes) for dc in st]
        return [i for i in await asyncio.gather(*task, return_exceptions=True) if i]


async def manage_storage(dc: StorageInfo, node, status_code, available_nodes) -> str:
    # If the proxy URL equals the node and storage proxy is enabled
    proxy_url = f"https://{node}"
    use_proxy = dc.webdav_policy == "use_proxy_url" or dc.web_proxy
    if dc.down_proxy_url != proxy_url or not use_proxy:
        return ""

    # Node is normal and storage is disabled
    if status_code == 200 and dc.disabled:
        await alist.storage_enable(dc.id)
        return f"🟢|<code>{node}</code>|Storage Enabled:\n<code>{dc.mount_path}</code>"
    # Node is unavailable and storage is enabled
    if status_code != 200 and not dc.disabled:
        # Enable auto-switch nodes if available
        if cf_cfg.auto_switch_nodes and available_nodes:
            random_node = random.choice(available_nodes)
            dc.down_proxy_url = random_node
            d = random_node.replace("https://", "")

            dc.remark = re_remark(dc.remark, d)

            await alist.storage_update(dc)
            return f"🟡|<code>{dc.mount_path}</code>\nAuto-switched node: <code>{node}</code> >> <code>{d}</code>"
        elif cf_cfg.storage_mgmt:
            await alist.storage_disable(dc.id)
            return f"🔴|<code>{node}</code>|Storage Disabled:\n<code>{dc.mount_path}</code>"


# Filter available nodes
async def returns_the_available_nodes(results: list[NodeStatus]) -> list:
    """
    Filter available nodes, remove used nodes
    :param results:
    :return:
    """
    # Available nodes
    node_pool = [f"https://{ns.url}" for ns in results if ns.status == 200]
    # Nodes already in use
    sl = (await alist.storage_list()).data
    used_node = [
        node.down_proxy_url
        for node in sl
        if node.webdav_policy == "use_proxy_url" or node.web_proxy
    ]
    # Remove used nodes from available nodes, reuse nodes if none are left
    return [x for x in node_pool if x not in used_node] or node_pool


# Send node status
async def notify_status_change(app: Client, node, status_code):
    t_l = {200: f"🟢|<code>{node}</code>|Recovered", 429: f"🔴|<code>{node}</code>|Offline"}
    text = t_l.get(status_code, f"⭕️|<code>{node}</code>|Error")
    logger.info(text) if status_code == 200 else logger.warning(text)

    if cf_cfg.status_push:
        for chat_id in cf_cfg.chat_id:
            try:
                await app.send_message(
                    chat_id=chat_id, text=text, parse_mode=ParseMode.HTML
                )
            except Exception as ex:
                logger.error(f"Failed to send node status | {chat_id}::{ex}")
