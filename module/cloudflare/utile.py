import datetime
from dataclasses import dataclass

import httpx
from aiocache import cached
from httpx import AsyncClient
from loguru import logger

from api.cloudflare.base import WorkerInfo
from api.cloudflare.cloudflare_api import CloudflareAPI
from config.config import CloudFlareInfo, cf_cfg
from tools.utils import pybyte


@dataclass
class NodeStatus:
    url: str
    status: int


# Check node status
@cached(
    ttl=cf_cfg.cache_ttl,
    key_builder=lambda f, *args, **kwargs: args[0],
    skip_cache_func=lambda ns: ns.status != 200,
)  # Cache for 5 minutes
async def check_node_status(url: str, cli: AsyncClient = None) -> NodeStatus:
    status_code_map = {
        200: [url, 200],
        401: [url, 200],
        429: [url, 429],
    }
    try:
        if cli:
            response = await cli.get(f"https://{url}")
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://{url}")
    except httpx.ConnectTimeout:
        return NodeStatus(url, 502)
    except httpx.ConnectError:
        return NodeStatus(url, 502)
    except httpx.ReadTimeout:
        return NodeStatus(url, 502)
    except Exception as e:
        logger.error(f"Node ({url}) status check failed - Unknown error | {type(e)} {e}")
        return NodeStatus(url, 502)
    return NodeStatus(*status_code_map.get(response.status_code, [url, 502]))


# Shift the current date by n days and return the shifted date along with the previous and next dates.
def date_shift(n: int = 0):
    tz_utc_0 = datetime.timezone.utc
    today = datetime.datetime.today().astimezone(tz=tz_utc_0)
    shifted_date = datetime.datetime.fromordinal(today.toordinal() + n)
    previous_date = datetime.datetime.fromordinal(shifted_date.toordinal() - 1)
    next_date = datetime.datetime.fromordinal(shifted_date.toordinal() + 1)
    previous_date_string = f"{previous_date.isoformat()}Z"
    next_date_string = f"{next_date.isoformat()}Z"
    return f"{shifted_date.isoformat()}Z", previous_date_string, next_date_string


@dataclass
class NodeInfo:
    text: str
    code: int
    worker_info: WorkerInfo


CODE_EMOJI = {
    200: "🟢",
    429: "🔴",
    502: "⭕️",
}


async def get_node_info(day: int, info: CloudFlareInfo) -> NodeInfo:
    """Get node information"""
    d = date_shift(day)
    wi = await CloudflareAPI(info.email, info.global_api_key).graphql_api(
        info.account_id, d[0], d[2], info.worker_name, info.page_name
    )
    code = await check_node_status(info.url)

    text = f"""
{info.url} | {CODE_EMOJI.get(code.status)}
Requests: <code>{wi.requests}</code> | Bandwidth: <code>{pybyte(wi.response_body_size)}</code>
———————"""

    return NodeInfo(text, code.status, wi)


def re_remark(remark: str, node: str):
    if "Node:" in remark:
        return "\n".join(
            [
                f"Node: {node}" if "Node:" in line else line
                for line in remark.split("\n")
            ]
        )
    return f"Node: {node}\n{remark}"
