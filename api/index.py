"""Vercel 진입점 — ASGI 앱을 `app`으로 노출한다.
엔드포인트: https://<프로젝트>.vercel.app/mcp
서버리스는 요청마다 인스턴스가 바뀔 수 있어 stateless 모드로 띄운다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import mcp  # noqa: E402

app = mcp.http_app(path="/mcp", stateless_http=True, json_response=True)
