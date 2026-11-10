"""도구 동작 확인: python -m pytest -q  (또는 python tests/test_tools.py)"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import Client  # noqa: E402

from server import mcp  # noqa: E402

TASKS = [
    {"name": "시장 조사", "start": "2026-08-01", "end": "2026-08-31"},
    {"name": "제품 기획", "start": "2026-09-01", "end": "2026-09-30"},
    {"name": "디자인", "start": "2026-09-15", "end": "2026-10-15"},
    {"name": "프로토타입 개발", "start": "2026-10-01", "end": "2026-11-15"},
    {"name": "테스트", "start": "2026-11-16", "end": "2026-12-15"},
    {"name": "최종 수정", "start": "2026-12-16", "end": "2026-12-25"},
    {"name": "출시 준비", "start": "2026-12-26", "end": "2026-12-31"},
]

SDLC_STEPS = [
    {"name": "요구사항 분석", "desc": "요구사항 명세서 작성"},
    {"name": "설계", "desc": "아키텍처·DB·UI 설계"},
    {"name": "코딩", "desc": "기능 구현·코드 리뷰"},
    {"name": "테스트", "desc": "단위·통합·인수 테스트"},
    {"name": "배포", "desc": "릴리스·모니터링"},
    {"name": "유지보수", "desc": "운영 지원·이슈 대응"},
]
SDLC_DECISIONS = [
    {"after": "요구사항 분석", "question": "요구사항 확정?", "branches": [{"label": "아니오", "to": "요구사항 분석"}]},
    {"after": "테스트", "question": "테스트 통과?", "branches": [
        {"label": "아니오: 버그", "to": "코딩"}, {"label": "아니오: 설계 결함", "to": "설계"}]},
    {"after": "유지보수", "question": "변경 요청 발생?", "branches": [
        {"label": "버그 수정", "to": "코딩"}, {"label": "신규 요구사항", "to": "요구사항 분석"},
        {"label": "서비스 종료", "to": "END"}]},
]


async def _call(name, args):
    async with Client(mcp) as c:
        r = await c.call_tool(name, args)
        return r.data


def test_list_tools():
    async def go():
        async with Client(mcp) as c:
            return {t.name for t in await c.list_tools()}
    assert asyncio.run(go()) == {"render_mermaid", "make_flowchart", "gantt_chart"}


def test_render_mermaid_adds_type():
    r = asyncio.run(_call("render_mermaid", {"source": "```mermaid\nA-->B\n```", "diagram_type": "flowchart"}))
    assert r["mermaid"].startswith("flowchart TD")
    assert r["png_url"].startswith("https://mermaid.ink/img/")


def test_sankey_korean_rejected():
    async def go():
        async with Client(mcp) as c:
            r = await c.call_tool("render_mermaid", {"source": "sankey-beta\n지원자,합격,10"}, raise_on_error=False)
            return r.is_error, str(r.content)
    is_err, msg = asyncio.run(go())
    assert is_err and "ASCII" in msg


def test_flowchart_sdlc():
    r = asyncio.run(_call("make_flowchart", {"steps": SDLC_STEPS, "decisions": SDLC_DECISIONS}))
    code = r["mermaid"]
    assert '-- "아니오: 버그" --> N2' in code and '--> E' in code and "classDef decision" in code


def test_gantt_workdays():
    r = asyncio.run(_call("gantt_chart", {"title": "신제품 출시", "tasks": TASKS, "today": "2026-11-11"}))
    assert [s["workdays"] for s in r["summary"]] == [21, 22, 23, 32, 22, 8, 4]
    assert r["total_workdays"] == 109
    assert r["svg"].startswith("<svg") and "excludes weekends" in r["mermaid"]


if __name__ == "__main__":
    for f in [test_list_tools, test_render_mermaid_adds_type, test_sankey_korean_rejected,
              test_flowchart_sdlc, test_gantt_workdays]:
        f()
        print("ok", f.__name__)
