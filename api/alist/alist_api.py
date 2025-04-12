# -*- coding: UTF-8 -*-
import base64
import datetime
import hashlib
import hmac
import os
from typing import Any, Dict, Literal, Type
from urllib import parse
from urllib.parse import urljoin

import httpx

from api.alist.base import (
    FileInfo,
    MetaInfo,
    SearchResultData,
    SettingInfo,
    StorageInfo,
    UserInfo,
)
from api.alist.base.base import AListAPIResponse, T
from config.config import bot_cfg

useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"


class AListAPI:
    def __init__(self, host, token):
        self.host = host
        self.token = token

        self.headers = {
            "UserAgent": useragent,
            "Content-Type": "application/json",
            "Authorization": self.token,
        }

    async def _request(
        self,
        method: Literal["GET", "POST", "PUT"],
        url,
        *,
        data_class: Type[T] = None,
        headers: Dict[str, str] = None,
        json: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        data: Any = None,
        timeout: int = 10,
    ) -> AListAPIResponse[T]:
        url = urljoin(self.host, url)
        headers = self.headers if headers is None else headers

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    url, headers=headers, params=params, timeout=timeout
                )
            elif method == "POST":
                response = await client.post(
                    url, headers=headers, json=json, timeout=timeout
                )
            elif method == "PUT":
                response = await client.put(
                    url, headers=headers, data=data, timeout=timeout
                )
        response.raise_for_status()
        result = response.json()
        return AListAPIResponse.from_dict(result, data_class)

    async def search(
        self,
        keywords,
        page: int = 1,
        per_page: int = 100,
        parent: str = "/",
        scope: int = 0,
        password: str = "",
    ):
        """Search for files"""
        body = {
            "parent": parent,
            "keywords": keywords,
            "scope": scope,
            "page": page,
            "per_page": per_page,
            "password": password,
        }
        return await self._request(
            "POST", "/api/fs/search", data_class=SearchResultData, json=body
        )

    async def fs_get(self, path):
        """Get download information"""
        return await self._request(
            "POST", "/api/fs/get", data_class=FileInfo, json={"path": path}
        )

    async def storage_get(self, storage_id):
        """Query specific storage information"""
        url = f"/api/admin/storage/get?id={storage_id}"
        return await self._request("GET", url, data_class=StorageInfo)

    async def storage_create(self, body: StorageInfo | dict):
        """Create new storage"""
        url = "/api/admin/storage/create"
        if isinstance(body, dict):
            body = StorageInfo.from_dict(body)
        return await self._request("POST", url, json=body.to_dict())

    async def storage_update(self, body: StorageInfo):
        """Update storage"""
        url = "/api/admin/storage/update"
        if isinstance(body, dict):
            body = StorageInfo.from_dict(body)
        return await self._request("POST", url, json=body.to_dict())

    async def storage_list(self):
        """Get storage list"""
        url = "/api/admin/storage/list"
        return await self._request("GET", url, data_class=StorageInfo)

    async def storage_delete(self, storage_id) -> AListAPIResponse:
        """Delete specific storage"""
        url = f"/api/admin/storage/delete?id={str(storage_id)}"
        return await self._request("POST", url)

    async def storage_enable(self, storage_id) -> AListAPIResponse:
        """Enable storage"""
        url = f"/api/admin/storage/enable?id={str(storage_id)}"
        return await self._request("POST", url)

    async def storage_disable(self, storage_id) -> AListAPIResponse:
        """Disable storage"""
        url = f"/api/admin/storage/disable?id={str(storage_id)}"
        return await self._request("POST", url)

    async def upload(
        self,
        local_path,
        remote_path,
        file_name,
        as_task: Literal["true", "false"] = "false",
    ):
        """Upload file"""
        url = "/api/fs/put"
        header = {
            "UserAgent": useragent,
            "As-Task": as_task,
            "Authorization": self.token,
            "File-Path": parse.quote(f"{remote_path}/{file_name}"),
            "Content-Length": f"{os.path.getsize(local_path)}",
        }
        return await self._request(
            "PUT",
            url,
            # data_class=UploadTaskResult,
            headers=header,
            data=open(local_path, "rb").read(),
        )

    async def fs_list(self, path, per_page: int = 0):
        """Get list, force refresh list"""
        url = "/api/fs/list"
        body = {"path": path, "page": 1, "per_page": per_page, "refresh": True}
        return await self._request("POST", url, json=body)

    async def driver_list(self):
        """Get driver list"""
        url = "/api/admin/driver/list"
        return await self._request("GET", url)

    async def setting_list(self):
        """Get settings list"""
        url = "/api/admin/setting/list"
        return await self._request("GET", url, data_class=SettingInfo)

    async def user_list(self):
        """Get user list"""
        url = "/api/admin/user/list"
        return await self._request("GET", url, data_class=UserInfo)

    async def meta_list(self):
        """Get metadata list"""
        url = "/api/admin/meta/list"
        return await self._request("GET", url, data_class=MetaInfo)

    async def setting_get(self, key):
        """Get a specific setting"""
        url = "/api/admin/setting/get"
        params = {"key": key}
        return await self._request("GET", url, data_class=SettingInfo, params=params)

    async def get_offline_download_tools(self):
        """Get offline download tools"""
        url = "/api/public/offline_download_tools"
        return await self._request("GET", url)

    async def add_offline_download(self, urls, tool, path, delete_policy):
        """Offline download"""
        url = "/api/fs/add_offline_download"
        body = {
            "delete_policy": delete_policy,
            "path": path,
            "tool": tool,
            "urls": urls,
        }
        return await self._request("POST", url, json=body)

    async def get_offline_download_undone_task(self):
        """Get unfinished offline download tasks"""
        url = "/api/admin/task/offline_download/undone"
        return await self._request("GET", url)

    async def get_offline_download_done_task(self):
        """Get completed offline download tasks"""
        url = "/api/admin/task/offline_download/done"
        return await self._request("GET", url)

    async def clear_offline_download_done_task(self):
        """Clear completed offline download tasks (including success/failure)"""
        url = "/api/admin/task/offline_download/clear_done"
        return await self._request("POST", url)

    @staticmethod
    def sign(path: str, expire_time: int = 30) -> str:
        """Calculate signature"""
        expire_time_stamp = int(
            datetime.datetime.now().timestamp()
            + datetime.timedelta(minutes=expire_time).total_seconds()
        )
        to_sign = f"{path}:{expire_time_stamp}"
        signature = hmac.new(
            bot_cfg.alist_token.encode(), to_sign.encode(), hashlib.sha256
        ).digest()
        _safe_base64 = base64.urlsafe_b64encode(signature).decode()
        return f"{_safe_base64}:{expire_time_stamp}"


alist = AListAPI(bot_cfg.alist_host, bot_cfg.alist_token)
