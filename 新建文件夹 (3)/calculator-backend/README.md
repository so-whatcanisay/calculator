# CalcSpace 后端

使用 Python 标准库实现的轻量计算器 API，采用安全的词法分析 + 逆波兰表达式求值，不使用 `eval` / `exec`，使用 SQLite 持久化计算历史。支持四则运算、括号、正负号、小数和平方根（如 `√(9)`）。

## 环境与启动

- Python 3.10+
- 无第三方依赖

```bash
python server.py
```

服务地址：`http://localhost:5050`
数据库文件：`data/calculator.db`（首次启动自动创建）

运行自动测试：

```bash
python -m unittest test_server.py
```

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/calculate` | 请求体 `{ "expression": "(1+2)*3" }`，服务端计算并写入数据库 |
| GET | `/api/history` | 查询历史记录 |
| DELETE | `/api/history/{id}` | 删除指定记录 |
| DELETE | `/api/history` | 清空历史 |

成功响应示例：`{"success":true,"expression":"(1+2)*3","result":9}`
错误响应示例：`{"success":false,"message":"除数不能为 0"}`
