import asyncio
import random

import aiocache
import httpx
from fastapi import Response
from loguru import logger
from starlette.responses import FileResponse, PlainTextResponse, RedirectResponse

from api.alist.alist_api import alist
from api.alist.base import SettingInfo
from api.alist.base.base import AListAPIResponse
from bot import fast
from config.config import cf_cfg, chat_data, plb_cfg
from module.cloudflare.utile import check_node_status
from tools.scheduler_manager import aps
from tools.utils import encode_url

TEXT_TYPES = []
REMOVE_PREFIX = True
REMOVE_PREFIX_TUPLE = (
    "down/",
    "proxy/",
)
limits = httpx.Limits(max_keepalive_connections=100, max_connections=1000)
async_client = httpx.AsyncClient(limits=limits)


@fast.get("/{path:path}")
async def redirect_path(path: str, sign: str | None = None):
    if not plb_cfg.enable:
        return PlainTextResponse("Proxy load balancing is disabled", status_code=503)

    path = encode_url(path, False)
    if not path:
        return Response(content="Running...", media_type="text/plain; charset=utf-8")
    if REMOVE_PREFIX and path.startswith(REMOVE_PREFIX_TUPLE):
        for i in REMOVE_PREFIX_TUPLE:
            path = path.removeprefix(i)
    r = await available_nodes()
    if not r:
        return FileResponse(
            status_code=503,
            path="./module/cloudflare/warning.txt",
            filename="All download node traffic for the website has been used up. It will automatically recover at 8 AM.txt",
        )
    new_url = f"https://{r}/{path}?sign={alist.sign(f'/{path}') if not sign else sign}"
    ext = path.split(".")[-1]
    if ext in TEXT_TYPES:
        return await forward_text(new_url)
    return RedirectResponse(url=encode_url(new_url), status_code=302)


def init_node(app):
    # Text files cannot be directly redirected, need to fetch file content first and then return
    global TEXT_TYPES
    r: AListAPIResponse[SettingInfo] = app.loop.run_until_complete(
        alist.setting_get("text_types")
    )
    TEXT_TYPES = r.data.value.split(",")
    app.loop.run_until_complete(refresh_nodes_regularly())
    aps.add_job(
        func=refresh_nodes_regularly,
        trigger="interval",
        job_id="returns_the_available_nodes",
        seconds=600,
    )


async def forward_text(new_url):
    """Handle text files"""
    response = await async_client.get(new_url)
    headers = dict(response.headers)
    headers.pop("content-encoding", None)
    headers.pop("content-length", None)
    return Response(
        content=response.content,
        media_type=headers["content-type"],
        headers=headers,
    )


async def available_nodes():
    """Randomly get an available node. If the same node is used continuously, it may be restricted due to high request volume."""
    if not (node_list := chat_data.get("node_list")):
        return
    return await random_node(node_list)


async def random_node(node_list):
    """Randomly select a node. If the node is unavailable, reselect."""
    r = await check_node_status(random.choice(node_list), async_client)
    return r.url if r.status == 200 else await random_node(node_list)


async def refresh_nodes_regularly():
    """Refresh the pool of available nodes"""
    # tasks = [get_node_info(i) for i in cf_cfg.nodes]
    # result_list = [
    #     result[0]
    #     for result in await asyncio.gather(*tasks, return_exceptions=True)
    #     if not isinstance(result, BaseException) and result[1] < 100000
    # ]
    cache = aiocache.decorators._get_cache()
    for node in cf_cfg.nodes:
        await cache.delete(key=node.url)
    tasks = [check_node_status(node.url) for node in cf_cfg.nodes]
    r = await asyncio.gather(*tasks, return_exceptions=True)
    node_list = []
    for i in r:
        if isinstance(i, BaseException):
            logger.error(f"Error refreshing node: {type(i)} {i}")
            continue
        if i.status == 200:
            node_list.append(i.url)

    chat_data["node_list"] = node_list
    logger.info(f"Nodes refreshed | {node_list}")
