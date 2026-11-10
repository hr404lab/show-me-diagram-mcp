# show-me-diagram-mcp

Remote MCP server that renders Mermaid diagrams from natural-language prompts — flowchart, gantt, mindmap, timeline, sankey, sequence.

AI에게 말로 설명하면 렌더링해주는 Mermaid 다이어그램 MCP 서버. Claude · ChatGPT · Gemini · 젠스파크 등 원격 MCP를 지원하는 어떤 AI에서도 쓸 수 있다. (Python + FastMCP, Vercel 배포)

| 도구 | 하는 일 | 대응 Claude 스킬 |
|---|---|---|
| `render_mermaid` | Mermaid 소스 정리(유형 보정·코드블록 제거) → 이미지·편집 URL | diagram-render |
| `make_flowchart` | 단계·의사결정·루프 구조 → 순서도 소스 + URL | process-flowchart |
| `gantt_chart` | Task 일정 → 주말·공휴일 제외 작업일, 상세 SVG, 이미지 URL | gantt-svg |

## 구조
```
show-me-diagram-mcp/
├─ server.py               # MCP 서버·도구 정의 + ASGI `app` (Vercel 자동 인식)
├─ diagram_tools/
│  ├─ mermaid.py           # 소스 정리, mermaid.ink URL 생성
│  ├─ flowchart.py         # 순서도 설계 규칙 → Mermaid
│  └─ gantt.py             # 작업일 계산, 의존성 추정, SVG
├─ tests/test_tools.py
└─ requirements.txt
```
엔드포인트: `/` 안내 페이지 · `/health` 상태 확인 · `/mcp` MCP (Streamable HTTP, stateless)

## 로컬 실행
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tests/test_tools.py      # 테스트 4개
python server.py                # http://localhost:8000/mcp
```

## Vercel 배포
1. GitHub(hr404lab)에 새 저장소로 push
2. vercel.com → Add New Project → 저장소 선택 → Deploy (설정 변경 없음)
3. 엔드포인트: `https://show-me-diagram-mcp.vercel.app/mcp`

## 연결
- **ChatGPT**: Settings → Security and login → Developer mode 켜기 → Plugins `+` → URL 입력 → 새 채팅에서 `+` → Developer mode → 앱 선택. (Plus 이상, 웹 전용 베타)
- **Claude**: 설정 → 커넥터 → 커스텀 커넥터 추가 → URL 입력
- **Gemini 앱**: 설정 → Connected Apps → Custom apps → Add a custom app → URL 입력 (웹에서 추가, 모바일 앱에도 반영)
- **Gemini CLI**: `~/.gemini/settings.json`의 `mcpServers`에 `"show-me-diagram": {"httpUrl": "https://show-me-diagram-mcp.vercel.app/mcp"}` 추가
- **젠스파크**: Skills → Connectors에서 커스텀 MCP 추가 메뉴 확인 (공식 문서에 절차 미기재)
- 각 서비스의 지침(Custom GPT Instructions 등)에 Claude 스킬 본문을 요약해 붙이면 결과 형식이 맞춰진다.

## 알아둘 점 / TODO
- **인증 없음(뼈대 단계)**. URL을 아는 누구나 호출 가능. 공개 전 OAuth(FastMCP auth provider) 추가 검토.
  ChatGPT는 고정 API 키 헤더 방식을 지원하지 않으므로 OAuth 또는 무인증 중 선택.
- **렌더링은 공개 서비스 mermaid.ink 사용** — 다이어그램 내용이 URL로 외부에 전달된다.
  사내 정보가 들어가면 Kroki 자체 호스팅 등으로 `diagram_tools/mermaid.py`의 `render_urls`만 교체.
- `gantt_chart`의 `svg`는 텍스트로 반환된다. 이를 그려주지 못하는 클라이언트를 위해
  같은 일정의 Mermaid gantt 이미지(`png_url`)를 함께 준다. 상세 SVG를 이미지 링크로 주려면
  Vercel Blob 등에 업로드하는 단계 추가.
- 공휴일은 자동 계산하지 않는다. `holidays`로 날짜를 넘긴다(추후 공휴일 API 연동).
