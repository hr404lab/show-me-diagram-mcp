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
    _check_sankey(s)
    return s


def _check_sankey(s: str) -> None:
    """Mermaid sankey 파서는 라벨에 ASCII만 허용한다(따옴표·문자코드로도 우회 불가, Mermaid 11 기준).
    한글 등이 있으면 원인과 대안을 담은 오류를 낸다."""
    lines = [ln for ln in s.splitlines() if ln.strip() and not ln.strip().startswith("%%")]
    if not lines or not lines[0].strip().startswith("sankey"):
        return
    bad = sorted({ch for ln in lines[1:] for ch in ln if ord(ch) > 127})
    if bad:
        raise ValueError(
            "Mermaid sankey는 라벨에 영문·숫자(ASCII)만 지원합니다(한글 불가). "
            "라벨을 영문으로 바꾸거나, 한글이 꼭 필요하면 D3 등으로 직접 그리세요. "
            f"문제 문자 예: {''.join(bad[:10])}"
        )


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
