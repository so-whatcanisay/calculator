"""CalcSpace API: safe expression parser plus SQLite history persistence."""
from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "calculator.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

FUNCTIONS = {"sqrt", "sin", "cos", "tan", "log", "ln", "log2", "exp", "abs", "round", "floor", "ceil", "factorial"}
TOKEN_RE = re.compile(r"\s*(?:(\d+(?:\.\d*)?|\.\d+)|([A-Za-z_][A-Za-z_0-9]*)|([+\-*/^(),!%√×÷−]))")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS calculation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expression TEXT NOT NULL,
        result REAL NOT NULL,
        created_at TEXT NOT NULL,
        favorite INTEGER NOT NULL DEFAULT 0
    )""")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(calculation_history)")}
    if "favorite" not in columns:
        conn.execute("ALTER TABLE calculation_history ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
    conn.commit()
    return conn


def tokenize(expression: str) -> list[tuple[str, str]]:
    if not expression or len(expression) > 200:
        raise ValueError("请输入 1-200 个字符的表达式")
    normalized = expression.replace("×", "*").replace("÷", "/").replace("−", "-")
    normalized = re.sub(r"√\s*(-?(?:\d+(?:\.\d*)?|\.\d+))", r"sqrt(\1)", normalized)
    normalized = normalized.replace("√", "sqrt")
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(normalized):
        match = TOKEN_RE.match(normalized, position)
        if not match:
            raise ValueError("表达式包含不支持的字符")
        number, identifier, symbol = match.groups()
        if number:
            tokens.append(("number", number))
        elif identifier:
            name = identifier.lower()
            if name in FUNCTIONS or name in {"pi", "e"}:
                tokens.append(("name", name))
            else:
                raise ValueError(f"不支持的函数或标识符：{identifier}")
        else:
            tokens.append(("symbol", symbol))
        position = match.end()
    tokens.append(("eof", ""))
    return tokens


class ExpressionParser:
    """Recursive descent parser; user input is never executed as Python code."""

    def __init__(self, expression: str):
        self.tokens = tokenize(expression)
        self.index = 0

    def current(self) -> tuple[str, str]:
        return self.tokens[self.index]

    def accept(self, value: str) -> bool:
        if self.current()[1] == value:
            self.index += 1
            return True
        return False

    def expect(self, value: str) -> None:
        if not self.accept(value):
            raise ValueError(f"缺少“{value}”或表达式格式不正确")

    def parse(self) -> float:
        result = self.parse_add_sub()
        if self.current()[0] != "eof":
            raise ValueError("表达式格式不正确")
        if not math.isfinite(result):
            raise ValueError("计算结果超出有限范围")
        return int(result) if result.is_integer() else round(result, 10)

    def parse_add_sub(self) -> float:
        value = self.parse_mul_div()
        while self.current()[1] in {"+", "-"}:
            operator = self.current()[1]
            self.index += 1
            right = self.parse_mul_div()
            value = value + right if operator == "+" else value - right
        return value

    def parse_mul_div(self) -> float:
        value = self.parse_unary()
        while self.current()[1] in {"*", "/"}:
            operator = self.current()[1]
            self.index += 1
            right = self.parse_unary()
            if operator == "/" and right == 0:
                raise ValueError("除数不能为 0")
            value = value * right if operator == "*" else value / right
        return value

    def parse_unary(self) -> float:
        if self.accept("+"):
            return self.parse_unary()
        if self.accept("-"):
            return -self.parse_unary()
        return self.parse_power()

    def parse_power(self) -> float:
        value = self.parse_postfix()
        if self.accept("^"):
            exponent = self.parse_unary()
            try:
                value = math.pow(value, exponent)
            except (OverflowError, ValueError):
                raise ValueError("幂运算结果无效或超出范围") from None
        return value

    def parse_postfix(self) -> float:
        value = self.parse_primary()
        while self.current()[1] in {"!", "%"}:
            operator = self.current()[1]
            self.index += 1
            if operator == "%":
                value /= 100
            else:
                if value < 0 or not value.is_integer() or value > 170:
                    raise ValueError("阶乘只支持 0 到 170 的整数")
                value = math.factorial(int(value))
        return value

    def parse_primary(self) -> float:
        token_type, token = self.current()
        if token_type == "number":
            self.index += 1
            return float(token)
        if token == "(":
            self.index += 1
            value = self.parse_add_sub()
            self.expect(")")
            return value
        if token_type == "name":
            self.index += 1
            if token == "pi":
                return math.pi
            if token == "e":
                return math.e
            if token == "sqrt" and self.current()[1] != "(":
                argument = self.parse_primary()
            else:
                self.expect("(")
                argument = self.parse_add_sub()
                self.expect(")")
            return self.apply_function(token, argument)
        raise ValueError("表达式格式不正确")

    @staticmethod
    def apply_function(name: str, value: float) -> float:
        try:
            if name == "sqrt":
                if value < 0:
                    raise ValueError("负数不能直接开平方")
                return math.sqrt(value)
            if name == "sin": return math.sin(math.radians(value))
            if name == "cos": return math.cos(math.radians(value))
            if name == "tan":
                if abs(math.cos(math.radians(value))) < 1e-12:
                    raise ValueError("tan 在该角度无定义")
                return math.tan(math.radians(value))
            if name == "log":
                if value <= 0: raise ValueError("log 的参数必须大于 0")
                return math.log10(value)
            if name == "ln":
                if value <= 0: raise ValueError("ln 的参数必须大于 0")
                return math.log(value)
            if name == "log2":
                if value <= 0: raise ValueError("log₂ 的参数必须大于 0")
                return math.log2(value)
            if name == "exp": return math.exp(value)
            if name == "abs": return abs(value)
            if name == "round": return round(value)
            if name == "floor": return math.floor(value)
            if name == "ceil": return math.ceil(value)
            if name == "factorial":
                if value < 0 or not value.is_integer() or value > 170:
                    raise ValueError("阶乘只支持 0 到 170 的整数")
                return math.factorial(int(value))
        except (OverflowError, ValueError):
            raise ValueError("函数参数或计算结果无效") from None
        raise ValueError("不支持的函数")


def evaluate(expression: str) -> float:
    return ExpressionParser(expression).parse()


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def do_OPTIONS(self) -> None:
        json_response(self, 204, {})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            json_response(self, 200, {"success": True, "service": "calcspace-api"})
            return
        if parsed.path != "/api/history":
            json_response(self, 404, {"success": False, "message": "接口不存在"})
            return
        query = parse_qs(parsed.query)
        keyword = query.get("q", [""])[0].strip()
        favorites_only = query.get("favorite", ["0"])[0] == "1"
        try:
            page = max(1, int(query.get("page", ["1"])[0]))
            page_size = min(100, max(1, int(query.get("page_size", ["20"])[0])))
        except ValueError:
            json_response(self, 400, {"success": False, "message": "分页参数无效"})
            return
        clauses, params = [], []
        if keyword:
            clauses.append("(expression LIKE ? OR CAST(result AS TEXT) LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if favorites_only:
            clauses.append("favorite = 1")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with get_db() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM calculation_history{where}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT id, expression, result, created_at, favorite FROM calculation_history{where} ORDER BY id DESC LIMIT ? OFFSET ?",
                [*params, page_size, (page - 1) * page_size],
            ).fetchall()
        json_response(self, 200, {"success": True, "data": [dict(row) for row in rows], "total": total, "page": page, "page_size": page_size})

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    @staticmethod
    def convert_base(payload: dict) -> str:
        value = str(payload.get("value", "")).strip().upper()
        from_base = int(payload.get("fromBase", 10))
        to_base = int(payload.get("toBase", 10))
        if from_base not in {2, 8, 10, 16} or to_base not in {2, 8, 10, 16}:
            raise ValueError("仅支持 2、8、10、16 进制")
        if not re.fullmatch(r"-?[0-9A-F]+", value):
            raise ValueError("进制输入必须是整数")
        number = int(value, from_base)
        if number == 0:
            return "0"
        sign = "-" if number < 0 else ""
        number = abs(number)
        digits = "0123456789ABCDEF"
        output = ""
        while number:
            output = digits[number % to_base] + output
            number //= to_base
        return sign + output

    @staticmethod
    def convert_unit(payload: dict) -> float:
        category = str(payload.get("category", "length"))
        source = str(payload.get("fromUnit", "m"))
        target = str(payload.get("toUnit", "m"))
        value = float(payload.get("value"))
        tables = {
            "length": {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000},
            "mass": {"mg": 0.000001, "g": 0.001, "kg": 1, "t": 1000},
            "temperature": {"C": 1, "F": 1, "K": 1},
        }
        if category not in tables or source not in tables[category] or target not in tables[category]:
            raise ValueError("不支持的单位组合")
        if category == "temperature":
            celsius = value if source == "C" else (value - 32) * 5 / 9 if source == "F" else value - 273.15
            result = celsius if target == "C" else celsius * 9 / 5 + 32 if target == "F" else celsius + 273.15
        else:
            result = value * tables[category][source] / tables[category][target]
        return int(result) if result.is_integer() else round(result, 10)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/calculate", "/api/convert/base", "/api/convert/unit"}:
            json_response(self, 404, {"success": False, "message": "接口不存在"})
            return
        try:
            payload = self.read_json()
            if path == "/api/convert/base":
                json_response(self, 200, {"success": True, "result": self.convert_base(payload)})
                return
            if path == "/api/convert/unit":
                json_response(self, 200, {"success": True, "result": self.convert_unit(payload)})
                return
            expression = str(payload.get("expression", "")).strip()
            result = evaluate(expression)
            created_at = datetime.now(timezone.utc).isoformat()
            with get_db() as conn:
                cursor = conn.execute("INSERT INTO calculation_history(expression, result, created_at) VALUES (?, ?, ?)", (expression, result, created_at))
                record_id = cursor.lastrowid
            json_response(self, 200, {"success": True, "id": record_id, "expression": expression, "result": result, "created_at": created_at, "favorite": 0})
        except (ValueError, json.JSONDecodeError, TypeError) as error:
            json_response(self, 400, {"success": False, "message": str(error)})
        except Exception as error:
            print("Unexpected error:", error)
            json_response(self, 500, {"success": False, "message": "服务器内部错误"})

    def do_PATCH(self) -> None:
        match = re.fullmatch(r"/api/history/(\d+)/favorite", urlparse(self.path).path)
        if not match:
            json_response(self, 404, {"success": False, "message": "接口不存在"})
            return
        try:
            favorite = 1 if bool(self.read_json().get("favorite")) else 0
            with get_db() as conn:
                cursor = conn.execute("UPDATE calculation_history SET favorite = ? WHERE id = ?", (favorite, int(match.group(1))))
            if cursor.rowcount == 0:
                json_response(self, 404, {"success": False, "message": "记录不存在"})
            else:
                json_response(self, 200, {"success": True, "favorite": favorite})
        except (ValueError, json.JSONDecodeError, TypeError) as error:
            json_response(self, 400, {"success": False, "message": str(error)})

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/history":
            with get_db() as conn:
                conn.execute("DELETE FROM calculation_history")
            json_response(self, 200, {"success": True})
            return
        match = re.fullmatch(r"/api/history/(\d+)", path)
        if match:
            with get_db() as conn:
                cursor = conn.execute("DELETE FROM calculation_history WHERE id = ?", (int(match.group(1)),))
            json_response(self, 200 if cursor.rowcount else 404, {"success": bool(cursor.rowcount), "message": "" if cursor.rowcount else "记录不存在"})
            return
        json_response(self, 404, {"success": False, "message": "接口不存在"})


if __name__ == "__main__":
    get_db().close()
    server = ThreadingHTTPServer(("0.0.0.0", 5050), Handler)
    print("CalcSpace API running at http://localhost:5050")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
