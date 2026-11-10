"""구조화된 단계·의사결정 정보 → 순서도 Mermaid 소스.

process-flowchart 스킬의 설계 규칙을 코드로 옮긴 것:
- 시작/종료는 타원, 단계는 사각형(굵은 제목 + 한 줄 설명), 의사결정은 다이아몬드
- 분기 라벨에 원인 표기, 역할별 색상 classDef
"""
from __future__ import annotations

import re

CLASS_DEFS = """  classDef step fill:#EAF1FB,stroke:#4F7CAC,color:#1F2D3D
  classDef decision fill:#FFF4DC,stroke:#D4A03C,color:#3D2E0A
  classDef term fill:#E8F5EC,stroke:#3E8E5E,color:#163A22"""


def _q(text: str) -> str:
    """Mermaid 라벨 안전 처리: 큰따옴표를 #quot;로."""
    return text.replace('"', "#quot;")


def _id(prefix: str, i: int) -> str:
    return f"{prefix}{i}"


def build_flowchart(
    steps: list[dict],
    decisions: list[dict] | None = None,
    direction: str = "TD",
) -> str:
    """
    steps: [{"name": "요구사항 분석", "desc": "요구사항 명세서 작성"}, ...]  (순서대로 연결)
    decisions: [{
        "after": "테스트",                 # 이 단계 뒤에 다이아몬드를 둔다
        "question": "테스트 통과?",
        "yes_label": "예",                  # 생략 시 '예' — 다음 단계로 진행
        "branches": [                       # 실패/기타 분기
            {"label": "아니오: 버그", "to": "코딩"},
            {"label": "서비스 종료", "to": "END"},   # END = 종료 노드
        ]
    }, ...]
    마지막 단계 뒤 다이아몬드에는 yes 분기가 없으면 자기 자신(유지)으로 돌아가는 분기를 넣지 않는다 —
    필요한 분기는 branches에 명시한다.
    """
    if not steps:
        raise ValueError("steps가 비어 있습니다.")
    direction = direction.upper() if direction.upper() in {"TD", "TB", "LR", "RL", "BT"} else "TD"
    decisions = decisions or []
    names = [s["name"] for s in steps]
    idx = {n: i for i, n in enumerate(names)}
    dec_by_step = {d["after"]: (k, d) for k, d in enumerate(decisions)}
    unknown = [d["after"] for d in decisions if d["after"] not in idx]
    if unknown:
        raise ValueError(f"decisions.after가 steps에 없습니다: {unknown}")

    lines = [f"flowchart {direction}", '  S(["시작"])', '  E(["종료"])']
    for i, s in enumerate(steps):
        label = f"<b>{i + 1}. {_q(s['name'])}</b>"
        if s.get("desc"):
            label += f"<br/>{_q(s['desc'])}"
        lines.append(f'  {_id("N", i)}["{label}"]')
    for k, d in enumerate(decisions):
        q = re.sub(r"\s+", " ", d["question"]).strip()
        if len(q) > 8 and "<br/>" not in q:
            cut = q.find(" ")
            q = q[:cut] + "<br/>" + q[cut + 1 :] if cut > 0 else q
        lines.append(f'  {_id("D", k)}{{"{_q(q)}"}}')

    lines.append(f"  S --> {_id('N', 0)}")
    used_end = False
    for i, n in enumerate(names):
        nxt = _id("N", i + 1) if i + 1 < len(names) else None
        if n in dec_by_step:
            k, d = dec_by_step[n]
            D = _id("D", k)
            lines.append(f"  {_id('N', i)} --> {D}")
            if nxt:
                lines.append(f'  {D} -- "{_q(d.get("yes_label", "예"))}" --> {nxt}')
            for b in d.get("branches", []):
                tgt = b["to"]
                if tgt.upper() == "END":
                    target, used_end = "E", True
                elif tgt in idx:
                    target = _id("N", idx[tgt])
                else:
                    raise ValueError(f"branches.to가 steps에 없습니다: {tgt}")
                lines.append(f'  {D} -- "{_q(b["label"])}" --> {target}')
        elif nxt:
            lines.append(f"  {_id('N', i)} --> {nxt}")
        else:
            lines.append(f"  {_id('N', i)} --> E")
            used_end = True
    if not used_end:
        lines.remove('  E(["종료"])')

    lines.append(CLASS_DEFS)
    lines.append(f"  class {','.join(_id('N', i) for i in range(len(steps)))} step")
    if decisions:
        lines.append(f"  class {','.join(_id('D', k) for k in range(len(decisions)))} decision")
    lines.append(f"  class S{',E' if used_end else ''} term")
    return "\n".join(lines)
