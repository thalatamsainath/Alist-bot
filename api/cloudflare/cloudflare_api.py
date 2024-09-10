from typing import Any, Dict, Literal

from cloudflare import AsyncCloudflare
from cloudflare.pagination import AsyncSinglePage, AsyncV4PagePaginationArray
from cloudflare.types.filters.firewall_filter import FirewallFilter
from cloudflare.types.pages.deployment import Deployment
from cloudflare.types.workers.script import Script
from cloudflare.types.zones.zone import Zone

from api.cloudflare.base import WorkerInfo


class CloudflareAPI:
    def __init__(self, email, key):
        self.email = email
        self.key = key
        self.client = AsyncCloudflare(api_email=self.email, api_key=self.key)

    async def list_accounts(self) -> AsyncV4PagePaginationArray[object]:
        return await self.client.accounts.list()

    async def _request(
        self,
        method: Literal["GET", "POST", "PUT"],
        url,
        *,
        headers: Dict[str, str] = None,
        json: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        data: Any = None,
        timeout: int = 10,
    ) -> dict:
        headers = self.client.default_headers if headers is None else headers
        if method == "GET":
            response = await self.client._client.get(
                url, headers=headers, params=params, timeout=timeout
            )
        elif method == "POST":
            response = await self.client._client.post(
                url, headers=headers, json=json, timeout=timeout
            )
        elif method == "PUT":
            response = await self.client._client.put(
                url, headers=headers, data=data, timeout=timeout
            )

        return response.json()

    async def list_zones(
        self,
    ) -> AsyncV4PagePaginationArray[Zone]:
        return await self.client.zones.list()

    async def get_workers_filter(
        self, zone_id
    ) -> AsyncV4PagePaginationArray[FirewallFilter]:
        return await self.client.filters.list(zone_id)

    async def list_workers(self, account_id) -> AsyncSinglePage[Script]:
        return await self.client.workers.scripts.list(account_id=account_id)

    async def list_pages(self, account_id) -> AsyncSinglePage[Deployment]:
        return await self.client.pages.projects.list(account_id=account_id)

    async def graphql_api(
        self,
        account_id: str,
        start: str,
        end: str,
        worker_name: str = "",
        page_name: str = "",
    ) -> WorkerInfo:
        if worker_name:
            return await self.graphql_api_worker(account_id, start, end, worker_name)
        elif page_name:
            return await self.graphql_api_page(account_id, start, end, page_name)
        raise

    async def graphql_api_worker(
        self, account_id, start, end, worker_name
    ) -> WorkerInfo:
        """获取worker数据
        :return dict
        {
          'data': {
            'viewer': {
              'accounts': [
                {
                  'workersInvocationsAdaptive': [
                    {
                      'sum': {
                        '__typename': 'AccountWorkersInvocationsAdaptiveSum',
                        'duration': 6195.5075318750005,
                        'errors': 2113,
                        'requests': 91946,
                        'responseBodySize': 277975284672,
                        'subrequests': 166371
                      }
                    }
                  ]
                }
              ]
            }
          },
          'errors': None
        }
        """
        url = "/graphql"
        query = """
query getBillingMetrics($accountTag: string, $datetimeStart: string, $datetimeEnd: string, $scriptName: string) {
    viewer {
      accounts(filter: {accountTag: $accountTag}) {
        workersInvocationsAdaptive(limit: 1000, filter: {
          scriptName: $scriptName,
          datetime_geq: $datetimeStart,
          datetime_leq: $datetimeEnd
        }) {
          sum {
          duration
          requests
          subrequests
          responseBodySize
          errors
          wallTime
          __typename
        }
        }
      }
    }
  }
"""
        variables = {
            "accountTag": account_id,
            "datetimeStart": start,
            "datetimeEnd": end,
            "scriptName": worker_name,
        }

        result = await self._request(
            "POST", url=url, json={"query": query, "variables": variables}
        )
        return WorkerInfo.from_dict(result)

    async def graphql_api_page(self, account_id, start, end, page_name) -> WorkerInfo:
        """获取worker数据
        :return dict
        {
          'data': {
            'viewer': {
              'accounts': [
                {
                  'workersInvocationsAdaptive': [
                    {
                      'sum': {
                        '__typename': 'AccountWorkersInvocationsAdaptiveSum',
                        'duration': 6195.5075318750005,
                        'errors': 2113,
                        'requests': 91946,
                        'responseBodySize': 277975284672,
                        'subrequests': 166371
                      }
                    }
                  ]
                }
              ]
            }
          },
          'errors': None
        }
        """
        url = "/graphql"
        query = """
query getBillingMetrics($accountTag: string, $scriptName: string, $datetimeStart: string, $datetimeEnd: string) {
  viewer {
    accounts(filter: {accountTag: $accountTag}) {
      workersInvocationsAdaptive: pagesFunctionsInvocationsAdaptiveGroups(limit: 1000, filter: {
          datetime_geq: $datetimeStart,
          datetime_leq: $datetimeEnd,
      		scriptName: $scriptName}) {
        sum {
          duration
          requests
          subrequests
          responseBodySize
          errors
          wallTime
          __typename
        }
      }
    }
  }
}
"""
        variables = {
            "accountTag": account_id,
            "datetimeStart": start,
            "datetimeEnd": end,
            "scriptName": page_name,
        }

        result = await self._request(
            "POST", url=url, json={"query": query, "variables": variables}
        )
        return WorkerInfo.from_dict(result)
