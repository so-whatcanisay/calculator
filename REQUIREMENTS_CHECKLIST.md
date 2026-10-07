# 作业要求核对表

| 要求 | 实现位置 | 状态 |
|---|---|---|
| 前端只提交表达式 JSON | `calculator-frontend/app.js` → `POST /api/calculate` | 已完成 |
| 后端完成全部计算 | `calculator-backend/server.py` 的 `ExpressionParser` | 已完成 |
| 加减乘除 | `ExpressionParser.parse_add_sub/parse_mul_div` | 已完成 |
| 括号与优先级 | 递归下降解析器 | 已完成 |
| 负数与小数 | `parse_unary`、数字词法分析 | 已完成 |
| 除零与非法表达式 | 后端 `ValueError` → HTTP 400 | 已完成 |
| 禁止 eval/exec | 白名单词法分析 + 递归下降解析 | 已完成 |
| SQLite 历史持久化 | `data/calculator.db`、`calculation_history` | 已完成 |
| 前端刷新重新读历史 | `GET /api/history` | 已完成 |
| 按 ID 删除历史 | `DELETE /api/history/{id}` | 已完成 |
| 清空全部历史 | `DELETE /api/history` | 已完成 |
| 后端停止无法产生新结果 | 前端所有结果请求依赖 `fetch` | 已验证 |
| 科学计算扩展 | sqrt、幂、三角、对数、指数、阶乘、取整等 | 已完成 |
| 进制转换扩展 | `POST /api/convert/base` | 已完成 |
| 单位换算扩展 | `POST /api/convert/unit` | 已完成 |
| 历史搜索/分页/收藏 | `/api/history?q&page&favorite`、PATCH 收藏 | 已完成 |
| 主题切换与键盘操作 | 前端 `app.js` | 已完成 |

## 已执行验证

- `python -m unittest test_server.py`：6 项测试全部通过。
- `python -m py_compile server.py`：通过。
- `node --check app.js`：通过。
- API 验证：`255` 十进制 → `FF` 十六进制；`1 km` → `1000 m`；历史收藏、搜索和删除均成功。
- 停止后端后，`POST /api/calculate` 请求失败，前端不能获得新的有效结果。
