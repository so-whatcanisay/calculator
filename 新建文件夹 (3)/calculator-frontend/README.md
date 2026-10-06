# CalcSpace 前端

基于原生 HTML/CSS/JavaScript 的前后端分离计算器前端，可直接使用 HBuilderX 打开 `index.html` 运行或预览。

## 功能

- 加减乘除、平方根、括号、优先级、小数和正负号表达式输入
- 通过 `POST /api/calculate` 请求后端计算并显示结果
- 从后端数据库读取计算历史，支持删除单条和清空全部
- 键盘操作、深色模式、连接状态提示和响应式布局

## 运行

1. 启动 `../calculator-backend/server.py`（默认 `http://localhost:5050`）。
2. 用 HBuilderX 打开本目录，运行 `index.html` 到浏览器。
3. 如后端部署到其他地址，修改 `app.js` 顶部的 `API_BASE`。

前端不在浏览器中计算最终结果，服务端停止时只能进行输入和界面操作，无法得到新的有效结果。
