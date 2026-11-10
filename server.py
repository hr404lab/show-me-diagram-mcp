"""show-me-diagram-mcp — Claude · ChatGPT · 젠스파크에서 공용으로 쓰는 다이어그램 MCP 서버.

도구
- render_mermaid : Mermaid 소스를 정리하고 이미지·편집 URL 반환  (diagram-render 스킬)
- make_flowchart : 단계·의사결정 구조 → 순서도 소스 + URL       (process-flowchart 스킬)
- gantt_chart    : Task 일정 → 작업일 계산 + SVG + 이미지 URL    (gantt-svg 스킬)

로컬 실행 : python server.py            → http://localhost:8000/mcp
Vercel     : api/index.py 가 ASGI 앱을 노출
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from diagram_tools.flowchart import build_flowchart
from diagram_tools.gantt import Dependency, Task, infer_dependencies, render_gantt_svg, workdays
from diagram_tools.mermaid import clean_source, render_urls

mcp = FastMCP(
    name="show-me-diagram",
    instructions=(
        "다이어그램 도구 모음. 사용자가 Mermaid 소스를 주면 render_mermaid, "
        "프로세스 설명만 주면 단계·의사결정을 설계해 make_flowchart, "
        "프로젝트 일정을 주면 gantt_chart를 호출한다. "
        "결과의 png_url 이미지를 답변에 보여주고, edit_url은 수정용 링크로 안내한다."
    ),
)


# ---------- 입력 스키마 ----------
class StepIn(BaseModel):
    name: str = Field(description="단계명, 예: 요구사항 분석")
    desc: str | None = Field(None, description="15자 안팎 한 줄 설명")


class BranchIn(BaseModel):
    label: str = Field(description="분기 라벨(원인 포함), 예: 아니오: 버그")
    to: str = Field(description="돌아갈 단계명, 또는 END(종료)")


class DecisionIn(BaseModel):
    after: str = Field(description="이 단계 뒤에 의사결정을 둔다(단계명)")
    question: str = Field(description="예: 테스트 통과?")
    yes_label: str = "예"
    branches: list[BranchIn] = Field(default_factory=list)


class TaskIn(BaseModel):
    name: str
    start: date = Field(description="YYYY-MM-DD")
    end: date = Field(description="YYYY-MM-DD")


class DependencyIn(BaseModel):
    pred: int = Field(description="선행 Task 번호(1부터)")
    succ: int = Field(description="후행 Task 번호(1부터)")
    kind: Literal["FS", "SS"] = "FS"


Theme = Literal["default", "neutral", "forest", "dark"]


# ---------- 도구 ----------
@mcp.tool
def render_mermaid(
    source: Annotated[str, "Mermaid 소스(코드블록 표시 있어도 됨)"],
    diagram_type: Annotated[str | None, "flowchart, sequenceDiagram, mindmap, sankey, timeline 등. 소스 첫 줄에 있으면 생략"] = None,
    theme: Theme = "default",
) -> dict:
    """Mermaid 소스를 정리(유형 선언 보정·코드블록 제거)하고 렌더링 이미지 URL과 편집 링크를 반환한다."""
    code = clean_source(source, diagram_type)
    return {"mermaid": code, **render_urls(code, theme)}


@mcp.tool
def make_flowchart(
    steps: list[StepIn],
    decisions: list[DecisionIn] | None = None,
    direction: Literal["TD", "LR"] = "TD",
    theme: Theme = "default",
) -> dict:
    """프로세스 단계와 의사결정(다이아몬드)·반복 루프 정보로 순서도를 만든다.
    단계는 입력 순서대로 연결되고, 의사결정의 branches로 이전 단계 복귀나 종료(END)를 표현한다."""
    code = build_flowchart(
        [s.model_dump() for s in steps],
        [d.model_dump() for d in (decisions or [])],
        direction,
    )
    return {"mermaid": code, **render_urls(code, theme)}


@mcp.tool
def gantt_chart(
    title: str,
    tasks: list[TaskIn],
    dependencies: Annotated[list[DependencyIn] | None, "생략하면 일정으로 FS/SS 추정"] = None,
    holidays: Annotated[list[date] | None, "제외할 공휴일 목록(YYYY-MM-DD)"] = None,
    today: Annotated[date | None, "오늘 표시선 날짜"] = None,
) -> dict:
    """Task 일정으로 간트차트를 만든다. 주말(·공휴일) 제외 작업일을 계산하고,
    상세 SVG(svg)와 어디서나 열리는 이미지 URL(png_url, Mermaid gantt 기반)을 함께 반환한다."""
    ts = [Task(t.name, t.start, t.end) for t in tasks]
    hs = set(holidays or [])
    deps = (
        [Dependency(d.pred - 1, d.succ - 1, d.kind) for d in dependencies]
        if dependencies is not None
        else infer_dependencies(ts)
    )
    svg = render_gantt_svg(title, ts, deps, today=today, holidays=hs)

    # SVG를 못 보여주는 클라이언트용: Mermaid gantt(주말 제외) 이미지
    mm = ["gantt", f"  title {title}", "  dateFormat YYYY-MM-DD", "  axisFormat %m/%d", "  excludes weekends"]
    mm += [f"  excludes {h.isoformat()}" for h in sorted(hs)]
    mm.append("  section Tasks")
    mm += [f"  {t.name.replace(':', ' ')} :t{i}, {t.start}, {t.end}" for i, t in enumerate(ts, 1)]
    mermaid_code = "\n".join(mm)

    return {
        "summary": [
            {"no": i, "task": t.name, "start": str(t.start), "end": str(t.end),
             "calendar_days": (t.end - t.start).days + 1, "workdays": workdays(t.start, t.end, hs)}
            for i, t in enumerate(ts, 1)
        ],
        "total_workdays": workdays(min(t.start for t in ts), max(t.end for t in ts), hs),
        "dependencies": [{"pred": d.pred + 1, "succ": d.succ + 1, "kind": d.kind} for d in deps],
        "svg": svg,
        "mermaid": mermaid_code,
        **render_urls(mermaid_code),
    }


# ---------- 안내 페이지 ----------
from starlette.requests import Request  # noqa: E402
from starlette.responses import HTMLResponse, JSONResponse  # noqa: E402

LANDING = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>show-me-diagram-mcp</title>
<style>body{font-family:system-ui,-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;max-width:640px;margin:48px auto;padding:0 16px;line-height:1.6;color:#1f2328;background:#fff}
code{background:#f3f4f6;padding:2px 6px;border-radius:4px}.ok{color:#1a7f37;font-weight:600}
@media(prefers-color-scheme:dark){body{background:#0d1117;color:#e6edf3}code{background:#161b22}.ok{color:#3fb950}}</style></head>
<body><h1>show-me-diagram-mcp</h1><p class="ok">● running</p>
<p>Remote MCP server that renders Mermaid diagrams from natural-language prompts.</p>
<p>Tools: <code>render_mermaid</code> <code>make_flowchart</code> <code>gantt_chart</code></p>
<p><a href="https://github.com/hr404lab/show-me-diagram-mcp">GitHub</a></p></body></html>"""


@mcp.custom_route("/", methods=["GET"], include_in_schema=False)
async def landing(request: Request) -> HTMLResponse:
    return HTMLResponse(LANDING)


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "tools": ["render_mermaid", "make_flowchart", "gantt_chart"]})


# ---------- ASGI 앱 (Vercel이 이 파일의 `app`을 자동 인식) ----------
# 서버리스는 요청마다 인스턴스가 바뀔 수 있어 stateless 모드로 띄운다.
from fastapi import FastAPI  # noqa: E402

mcp_app = mcp.http_app(path="/mcp", stateless_http=True, json_response=True)
app = FastAPI(title="show-me-diagram-mcp", lifespan=mcp_app.lifespan, docs_url=None, redoc_url=None)
app.mount("/", mcp_app)  # /, /health, /mcp 모두 mcp_app이 처리


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
