"""CalcSpace calculator API. Safe parser + SQLite persistence, no eval/exec."""
from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "calculator.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS calculation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expression TEXT NOT NULL,
        result REAL NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn


def tokenize(expression: str) -> list[str]:
    compact = expression.replace("×", "*").replace("÷", "/").replace("−", "-").strip()
    if not compact or len(compact) > 200:
        raise ValueError("请输入 1-200 个字符的表达式")
    if not re.fullmatch(r"[0-9+\-*/().√\s]+", compact):
        raise ValueError("表达式包含不支持的字符")
    raw = re.findall(r"\d+(?:\.\d+)?|\.\d+|[+\-*/()√]", compact)
    if "".join(raw).replace(" ", "") != re.sub(r"\s+", "", compact):
        raise ValueError("表达式格式不正确")
    tokens: list[str] = []
    previous: str | None = None
    for token in raw:
        if token == "√":
            token = "sqrt"
        if token in ("+", "-") and (previous is None or previous in "+-*/("):
            token = "u" + token
        tokens.append(token)
        previous = token
    return tokens


def evaluate(expression: str) -> float:
    tokens = tokenize(expression)
    precedence = {"u+": 4, "u-": 4, "sqrt": 4, "*": 2, "/": 2, "+": 1, "-": 1}
    right_assoc = {"u+", "u-", "sqrt"}
    output: list[str] = []
    operators: list[str] = []
    for token in tokens:
        if re.fullmatch(r"\d+(?:\.\d+)?|\.\d+", token):
            output.append(token)
        elif token in precedence:
            while operators and operators[-1] in precedence:
                top = operators[-1]
                should_pop = (token not in right_assoc and precedence[token] <= precedence[top]) or (token in right_assoc and precedence[token] < precedence[top])
                if not should_pop:
                    break
                output.append(operators.pop())
            operators.append(token)
        elif token == "(":
            operators.append(token)
        elif token == ")":
            while operators and operators[-1] != "(":
                output.append(operators.pop())
            if not operators:
                raise ValueError("括号不匹配")
            operators.pop()
        else:
            raise ValueError("表达式格式不正确")
    while operators:
        if operators[-1] in "()":
            raise ValueError("括号不匹配")
        output.append(operators.pop())
    values: list[float] = []
    for token in output:
        if re.fullmatch(r"\d+(?:\.\d+)?|\.\d+", token):
            values.append(float(token))
        elif token in ("u+", "u-", "sqrt"):
            if not values:
                raise ValueError("一元运算符缺少数字")
            value = values.pop()
            if token == "u+": values.append(value)
            elif token == "u-": values.append(-value)
            else:
                if value < 0: raise ValueError("负数不能直接开平方")
                values.append(math.sqrt(value))
        else:
            if len(values) < 2:
                raise ValueError("表达式格式不正确")
            right, left = values.pop(), values.pop()
            if token == "+": values.append(left + right)
            elif token == "-": values.append(left - right)
            elif token == "*": values.append(left * right)
            elif token == "/":
                if right == 0: raise ValueError("除数不能为 0")
                values.append(left / right)
    if len(values) != 1 or not math.isfinite(values[0]):
        raise ValueError("表达式格式不正确")
    result = values[0]
    return int(result) if result.is_integer() else round(result, 10)


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def do_OPTIONS(self) -> None:
        json_response(self, 204, {})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            json_response(self, 200, {"success": True, "service": "calcspace-api"})
        elif path == "/api/history":
            with get_db() as conn:
                rows = conn.execute("SELECT id, expression, result, created_at FROM calculation_history ORDER BY id DESC").fetchall()
            json_response(self, 200, {"success": True, "data": [dict(row) for row in rows]})
        else:
            json_response(self, 404, {"success": False, "message": "接口不存在"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/calculate":
            json_response(self, 404, {"success": False, "message": "接口不存在"}); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            expression = str(payload.get("expression", "")).strip()
            result = evaluate(expression)
            created_at = datetime.now(timezone.utc).isoformat()
            with get_db() as conn:
                cursor = conn.execute("INSERT INTO calculation_history(expression, result, created_at) VALUES (?, ?, ?)", (expression, result, created_at))
                record_id = cursor.lastrowid
            json_response(self, 200, {"success": True, "id": record_id, "expression": expression, "result": result, "created_at": created_at})
        except (ValueError, json.JSONDecodeError, TypeError) as error:
            json_response(self, 400, {"success": False, "message": str(error)})
        except Exception as error:
            print("Unexpected error:", error)
            json_response(self, 500, {"success": False, "message": "服务器内部错误"})

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/history":
            with get_db() as conn: conn.execute("DELETE FROM calculation_history")
            json_response(self, 200, {"success": True})
            return
        match = re.fullmatch(r"/api/history/(\d+)", path)
        if match:
            with get_db() as conn:
                cursor = conn.execute("DELETE FROM calculation_history WHERE id = ?", (int(match.group(1)),))
            if cursor.rowcount == 0: json_response(self, 404, {"success": False, "message": "记录不存在"})
            else: json_response(self, 200, {"success": True})
            return
        json_response(self, 404, {"success": False, "message": "接口不存在"})


if __name__ == "__main__":
    get_db().close()
    server = ThreadingHTTPServer(("0.0.0.0", 5050), Handler)
    print("CalcSpace API running at http://localhost:5050")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
