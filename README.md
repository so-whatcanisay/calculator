# CalcSpace 前后端分离计算器作业

本仓库包含两个可独立提交的项目目录：

- `calculator-frontend/`：HBuilderX 可打开的 Web 前端
- `calculator-backend/`：Python + SQLite 后端 API

先启动后端，再用 HBuilderX 运行前端即可完成联调。作业设计、API、PSP 和验收说明见 [`assignment-blog.md`](assignment-blog.md)。

当前功能覆盖：基础/复合表达式、科学计算、进制转换、单位换算、数据库历史、历史搜索、分页、收藏、单条删除、全部清空、主题切换和断开连接提示。

后端测试：`cd calculator-backend && python -m unittest test_server.py`。

逐项验收记录见 [`REQUIREMENTS_CHECKLIST.md`](REQUIREMENTS_CHECKLIST.md)。
