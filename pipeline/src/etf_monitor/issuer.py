"""운용사 매핑.

종목명 첫 토큰(브랜드 prefix)으로 운용사를 식별한다.
리브랜딩 이력은 ``data/issuer_map.yaml`` 의 ``aliases`` 에 보존한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Issuer:
    brand: str
    issuer: str
    issuer_en: str
    aliases: tuple[str, ...]
    note: str = ""


class IssuerMap:
    """브랜드 prefix → ``Issuer`` 매핑.

    ``aliases`` 는 같은 운용사의 *과거* 브랜드를 가리키며,
    조회 시 현재 브랜드의 ``Issuer`` 로 일관되게 통합한다.
    """

    def __init__(self, brands: dict[str, Issuer]) -> None:
        self._brands = brands
        self._lookup: dict[str, Issuer] = {}
        for brand, info in brands.items():
            self._lookup[brand.upper()] = info
            for alias in info.aliases:
                self._lookup[alias.upper()] = info

    @classmethod
    def load(cls, path: Path) -> "IssuerMap":
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        brands: dict[str, Issuer] = {}
        for brand, info in raw.items():
            brands[brand] = Issuer(
                brand=brand,
                issuer=info.get("issuer", brand),
                issuer_en=info.get("issuer_en", ""),
                aliases=tuple(info.get("aliases") or []),
                note=info.get("note", ""),
            )
        logger.info("issuer_map loaded: %d brands", len(brands))
        return cls(brands)

    def resolve(self, item_name: str) -> Issuer | None:
        """종목명에서 운용사 ``Issuer`` 를 찾는다.

        매칭 규칙: 종목명을 공백/언더스코어/하이픈으로 토큰화한 첫 토큰을
        대문자로 정규화 후 lookup 한다. 매칭 실패 시 None.
        """
        if not item_name:
            return None
        head = _first_token(item_name).upper()
        return self._lookup.get(head)

    @property
    def brands(self) -> dict[str, Issuer]:
        return dict(self._brands)


def _first_token(text: str) -> str:
    for sep in (" ", "_", "-"):
        text = text.replace(sep, " ")
    head = text.strip().split(" ", 1)[0]
    return head


@lru_cache(maxsize=1)
def get_issuer_map(path: str | Path) -> IssuerMap:
    return IssuerMap.load(Path(path))
