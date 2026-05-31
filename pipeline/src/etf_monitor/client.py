"""공공데이터포털 API 클라이언트.

* 일반 인증키(Decoding 키)를 ``serviceKey`` 쿼리 파라미터로 그대로 전달한다.
* JSON 응답을 가정하며 ``resultType=json`` 을 강제한다.
* 페이지네이션은 ``totalCount`` 가 응답에 포함되는 공공데이터포털 표준 응답 구조를
  전제로 한다 (``response.body.{totalCount,numOfRows,pageNo,items.item}``).
* 응답 스키마가 명세서와 다르면 :func:`_extract_items` 한 곳만 조정하면 된다.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 1000
MAX_RETRIES = 3
BACKOFF_SECONDS = 1.5


class PublicDataApiError(RuntimeError):
    pass


class PublicDataClient:
    def __init__(self, service_key: str, *, timeout: int = DEFAULT_TIMEOUT) -> None:
        if not service_key:
            raise ValueError("service_key 가 비어 있습니다. .env 의 DATA_GO_KR_KEY 를 확인하세요.")
        self.service_key = service_key
        self.timeout = timeout
        self.session = requests.Session()

    # ----------------------------------------------------------------------------------
    # 단일 호출
    # ----------------------------------------------------------------------------------

    def call(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        merged = {
            "serviceKey": self.service_key,
            "resultType": "json",
            **params,
        }
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=merged, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                self._raise_if_api_error(data)
                return data
            except (requests.RequestException, ValueError) as exc:
                if attempt >= MAX_RETRIES:
                    raise PublicDataApiError(f"GET {url} failed after {attempt} attempts: {exc}") from exc
                sleep = BACKOFF_SECONDS * attempt
                logger.warning("call failed (%s). retrying in %.1fs ...", exc, sleep)
                time.sleep(sleep)
        raise PublicDataApiError("unreachable")  # pragma: no cover

    # ----------------------------------------------------------------------------------
    # 페이지네이션
    # ----------------------------------------------------------------------------------

    def paginate(
        self,
        url: str,
        params: dict[str, Any],
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            payload = self.call(url, {**params, "numOfRows": page_size, "pageNo": page})
            items = self._extract_items(payload)
            if not items:
                return
            yield from items
            total, page_no, num_of_rows = self._extract_paging(payload)
            if total is None:
                if len(items) < page_size:
                    return
            else:
                if page_no * num_of_rows >= total:
                    return
            page += 1

    # ----------------------------------------------------------------------------------
    # 응답 파싱 (명세서 기준 조정 가능 지점)
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _raise_if_api_error(payload: dict[str, Any]) -> None:
        # 공공데이터포털 표준 에러 형태: {"OpenAPI_ServiceResponse": {"cmmMsgHeader": {...}}}
        err = payload.get("OpenAPI_ServiceResponse")
        if err:
            header = err.get("cmmMsgHeader", {})
            raise PublicDataApiError(
                f"API error: {header.get('returnReasonCode')} {header.get('errMsg')} "
                f"(authMsg: {header.get('returnAuthMsg')})"
            )
        body = (payload.get("response") or {}).get("header") or {}
        result_code = body.get("resultCode")
        if result_code is not None and str(result_code) not in ("00", "0"):
            raise PublicDataApiError(
                f"API error: code={result_code} msg={body.get('resultMsg')}"
            )

    @staticmethod
    def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        body = (payload.get("response") or {}).get("body") or {}
        items_node = body.get("items") or {}
        if isinstance(items_node, dict):
            inner = items_node.get("item")
        else:
            inner = items_node
        if inner is None:
            return []
        if isinstance(inner, dict):
            return [inner]
        return list(inner)

    @staticmethod
    def _extract_paging(payload: dict[str, Any]) -> tuple[int | None, int, int]:
        body = (payload.get("response") or {}).get("body") or {}
        try:
            total = int(body.get("totalCount")) if body.get("totalCount") is not None else None
        except (TypeError, ValueError):
            total = None
        try:
            page_no = int(body.get("pageNo") or 1)
        except (TypeError, ValueError):
            page_no = 1
        try:
            num_of_rows = int(body.get("numOfRows") or DEFAULT_PAGE_SIZE)
        except (TypeError, ValueError):
            num_of_rows = DEFAULT_PAGE_SIZE
        return total, page_no, num_of_rows
