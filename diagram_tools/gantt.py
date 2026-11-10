"""간트차트 SVG 생성 — 주말 제외 작업일, FS/SS 의존성, 오늘 표시."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from html import escape

PALETTE = ["#4F7CAC", "#5B9A8B", "#C47A5A", "#8E6BB0", "#D4A03C", "#C0566B", "#3E8E5E"]
FONT = "Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif"


@dataclass
class Task:
    name: str
    start: date
    end: date


@dataclass
class Dependency:
    pred: int  # 선행 Task 인덱스(0부터)
    succ: int  # 후행 Task 인덱스
    kind: str = "FS"  # "FS" 또는 "SS"


def workdays(a: date, b: date, holidays: set[date] | None = None) -> int:
    holidays = holidays or set()
    return sum(
        1
        for i in range((b - a).days + 1)
        if (d := a + timedelta(i)).weekday() < 5 and d not in holidays
    )


def infer_dependencies(tasks: list[Task]) -> list[Dependency]:
    """의존성이 주어지지 않았을 때 일정으로 추정한다.
    - 선행 종료 직후(평일 기준) 시작 → FS
    - 선행 진행 중 시작(겹침) → SS
    각 Task는 가장 가까운 선행 1개(FS 우선)만 연결한다.
    """
    deps: list[Dependency] = []
    for j, t in enumerate(tasks):
        fs = [i for i in range(j) if 0 < (t.start - tasks[i].end).days <= 3]
        ss = [i for i in range(j) if tasks[i].start <= t.start <= tasks[i].end]
        for i in fs:
            deps.append(Dependency(i, j, "FS"))
        if ss:
            deps.append(Dependency(max(ss), j, "SS"))
    return deps


def render_gantt_svg(
    title: str,
    tasks: list[Task],
    deps: list[Dependency] | None = None,
    today: date | None = None,
    holidays: set[date] | None = None,
) -> str:
    if not tasks:
        raise ValueError("tasks가 비어 있습니다.")
    holidays = holidays or set()
    deps = infer_dependencies(tasks) if deps is None else deps
    S = min(t.start for t in tasks)
    E = max(t.end for t in tasks)
    N = (E - S).days + 1

    W, L = 1240, 330
    X0, X1 = L, W - 30
    dw = (X1 - X0) / N
    top, rowH, barH = 110, 46, 22
    H = top + rowH * len(tasks) + 90

    def x(d: date) -> float:
        return X0 + (d - S).days * dw

    def off(d: date) -> bool:
        return d.weekday() >= 5 or d in holidays

    o: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
        '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker></defs>',
        f'<rect width="{W}" height="{H}" fill="#fff"/>',
        f'<text x="30" y="38" font-size="22" font-weight="700" fill="#222">{escape(title)}</text>',
        f'<text x="30" y="62" font-size="13" fill="#666">{S:%Y.%m.%d} – {E:%Y.%m.%d} · '
        f'전체 {workdays(S, E, holidays)} 작업일 (주말{"·공휴일" if holidays else ""} 제외)</text>',
    ]
    rows_h = rowH * len(tasks)
    for i in range(len(tasks)):
        if i % 2 == 0:
            o.append(f'<rect x="20" y="{top + i * rowH}" width="{W - 40}" height="{rowH}" fill="#F7F8FA"/>')
    for i in range(N):
        d = S + timedelta(i)
        if off(d):
            o.append(f'<rect x="{x(d):.2f}" y="{top - 28}" width="{dw:.2f}" height="{rows_h + 28}" fill="#E6E8EC" opacity="0.6"/>')

    m = date(S.year, S.month, 1)
    while m <= E:
        nm = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        ms, me = max(m, S), min(nm - timedelta(1), E)
        o.append(f'<line x1="{x(ms):.2f}" y1="{top - 42}" x2="{x(ms):.2f}" y2="{top + rows_h}" stroke="#BFC4CC"/>')
        o.append(
            f'<text x="{(x(ms) + x(me) + dw) / 2:.2f}" y="{top - 34}" font-size="13" font-weight="600" fill="#333" '
            f'text-anchor="middle">{m.month}월 ({workdays(ms, me, holidays)}일)</text>'
        )
        m = nm
    for i in range(N):
        d = S + timedelta(i)
        if d.weekday() == 0:
            o.append(f'<text x="{x(d) + 1:.2f}" y="{top - 6}" font-size="9" fill="#888">{d.day}</text>')
    o.append(f'<line x1="{X1}" y1="{top - 42}" x2="{X1}" y2="{top + rows_h}" stroke="#BFC4CC"/>')
    o.append(f'<text x="30" y="{top - 10}" font-size="12" font-weight="700" fill="#555">Task</text>')
    o.append(f'<text x="{L - 12}" y="{top - 10}" font-size="12" font-weight="700" fill="#555" text-anchor="end">작업일</text>')

    pos = []
    for i, t in enumerate(tasks):
        c = PALETTE[i % len(PALETTE)]
        y = top + i * rowH
        by = y + (rowH - barH) / 2
        o.append(f'<text x="30" y="{y + 21}" font-size="14" font-weight="600" fill="#222">{i + 1}. {escape(t.name)}</text>')
        o.append(
            f'<text x="30" y="{y + 37}" font-size="11" fill="#777">{t.start.month}/{t.start.day} – '
            f'{t.end.month}/{t.end.day} ({(t.end - t.start).days + 1}일)</text>'
        )
        o.append(
            f'<text x="{L - 12}" y="{y + 28}" font-size="14" font-weight="700" fill="{c}" '
            f'text-anchor="end">{workdays(t.start, t.end, holidays)}일</text>'
        )
        o.append(f'<rect x="{x(t.start):.2f}" y="{by}" width="{((t.end - t.start).days + 1) * dw:.2f}" height="{barH}" rx="4" fill="{c}" opacity="0.22"/>')
        d = t.start
        first = last = None
        while d <= t.end:
            if not off(d):
                e = d
                while e + timedelta(1) <= t.end and not off(e + timedelta(1)):
                    e += timedelta(1)
                o.append(f'<rect x="{x(d):.2f}" y="{by}" width="{((e - d).days + 1) * dw:.2f}" height="{barH}" fill="{c}"/>')
                first = first or d
                last = e
                d = e
            d += timedelta(1)
        first, last = first or t.start, last or t.end
        pos.append((x(first), x(last) + dw, by + barH / 2, by, by + barH))

    for dep in deps:
        if not (0 <= dep.pred < len(tasks) and 0 <= dep.succ < len(tasks)):
            continue
        ps, pe, pm, pt, pb = pos[dep.pred]
        ss, se, sm, st, sb = pos[dep.succ]
        if dep.kind.upper() == "SS":
            path, dash = f"M{ps:.1f},{pb} V{st - 6:.1f} H{ss + 4:.1f} V{st - 1:.1f}", "4 3"
        else:
            if ss - pe > 12:
                mid = ss - 6
                path = f"M{pe:.1f},{pm} H{mid:.1f} V{sm} H{ss - 1:.1f}"
            else:
                path = f"M{pe:.1f},{pm} H{pe + 6:.1f} V{(pb + sm) / 2:.1f} H{ss - 8:.1f} V{sm} H{ss - 1:.1f}"
            dash = "none"
        o.append(f'<path d="{path}" fill="none" stroke="#555" stroke-width="1.3" stroke-dasharray="{dash}" marker-end="url(#ar)"/>')

    if today and S <= today <= E:
        tx = x(today) + dw / 2
        o.append(f'<line x1="{tx:.2f}" y1="{top - 28}" x2="{tx:.2f}" y2="{top + rows_h}" stroke="#E0443A" stroke-width="1.5"/>')
        o.append(f'<text x="{tx:.2f}" y="{top + rows_h + 14}" font-size="11" fill="#E0443A" text-anchor="middle">오늘 {today.month}/{today.day}</text>')

    ly = H - 36
    o += [
        f'<rect x="30" y="{ly - 10}" width="22" height="12" fill="#4F7CAC"/><text x="58" y="{ly}" font-size="12" fill="#444">작업일</text>',
        f'<rect x="120" y="{ly - 10}" width="22" height="12" fill="#4F7CAC" opacity="0.22"/><text x="148" y="{ly}" font-size="12" fill="#444">비작업일</text>',
        f'<rect x="240" y="{ly - 10}" width="22" height="12" fill="#E6E8EC"/><text x="268" y="{ly}" font-size="12" fill="#444">주말{"·공휴일" if holidays else ""} 음영</text>',
        f'<line x1="380" y1="{ly - 4}" x2="410" y2="{ly - 4}" stroke="#555" stroke-width="1.3" marker-end="url(#ar)"/><text x="418" y="{ly}" font-size="12" fill="#444">FS (선행 종료 → 후행 시작)</text>',
        f'<line x1="610" y1="{ly - 4}" x2="640" y2="{ly - 4}" stroke="#555" stroke-width="1.3" stroke-dasharray="4 3" marker-end="url(#ar)"/><text x="648" y="{ly}" font-size="12" fill="#444">SS (선행 시작 후 병행 착수)</text>',
        f'<text x="30" y="{H - 12}" font-size="11" fill="#888">※ {"공휴일 반영" if holidays else "공휴일 미반영, 주말만 제외"}. 월 아래 숫자는 해당 주 월요일 날짜.</text>',
        "</svg>",
    ]
    return "\n".join(o)
