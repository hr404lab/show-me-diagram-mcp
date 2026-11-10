"""Mermaid 소스 정리 + 렌더링 URL 생성.

서버리스(Vercel)에는 브라우저가 없어 직접 렌더링하지 않고,
공개 렌더러 mermaid.ink의 이미지 URL을 만들어 돌려준다.
(사내 데이터처럼 외부로 보내면 안 되는 내용이면 자체 렌더러로 교체할 것 — README 참고)
"""
from __future__ import annotations

import base64
import json
import re

# 사용자가 흔히 쓰는 이름 → Mermaid 정식 키워드
TYPE_ALIASES = {
    "sankey": "sankey-beta",
    "state": "stateDiagram-v2",
    "statediagram": "stateDiagram-v2",
    "flowchart": "flowchart TD",
    "graph": "flowchart TD",
    "sequence": "sequenceDiagram",
    "class": "classDiagram",
    "er": "erDiagram",
    "xychart": "xychart-beta",
}

KNOWN_HEADS = (
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram",
    "journey", "gantt", "pie", "quadrantChart", "requirementDiagram", "gitGraph", "mindmap",
    "timeline", "sankey-beta", "xychart-beta", "block-beta", "C4Context", "architecture-beta",
    "%%{",  # init 지시문으로 시작하는 경우
)


def normalize_type(diagram_type: str | None) -> str | None:
    if not diagram_type:
        return None
    t = diagram_type.strip()
    return TYPE_ALIASES.get(t.lower(), t)


def clean_source(source: str, diagram_type: str | None = None) -> str:
    """코드블록 표시 제거, 유형 선언이 없으면 첫 줄에 붙인다."""
    s = source.strip()
    s = re.sub(r"^```(?:mermaid)?\s*\n?", "", s)
    s = re.sub(r"\n?```\s*$", "", s).strip()
    first = s.splitlines()[0].strip() if s else ""
    if not first.startswith(KNOWN_HEADS):
        t = normalize_type(diagram_type)
        if not t:
            raise ValueError("다이어그램 유형을 알 수 없습니다. diagram_type을 지정하거나 소스 첫 줄에 선언하세요.")
        s = f"{t}\n{s}"
    return s


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def render_urls(source: str, theme: str = "default") -> dict:
    """mermaid.ink 이미지 URL과 Mermaid Live 편집 링크."""
    enc = _b64url(source)
    live_state = _b64url(json.dumps({"code": source, "mermaid": {"theme": theme}}))
    return {
        "svg_url": f"https://mermaid.ink/svg/{enc}?theme={theme}",
        "png_url": f"https://mermaid.ink/img/{enc}?type=png&theme={theme}",
        "edit_url": f"https://mermaid.live/edit#base64:{live_state}",
    }
