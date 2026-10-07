# 前端代码规范

规范来源：Google JavaScript Style Guide（https://google.github.io/styleguide/jsguide.html）与 Airbnb JavaScript Style Guide。

- 使用 2 个空格缩进，语句末尾使用分号。
- 变量和函数使用 `camelCase`，常量使用大写下划线命名。
- 优先使用 `const`，需要重新赋值时使用 `let`，不使用 `var`。
- DOM 事件通过 `addEventListener` 绑定，避免内联事件处理器。
- 用户可见文本使用中文，错误信息应说明可采取的操作。
- 网络请求集中封装，所有异步请求处理失败分支。
- HTML 使用语义化元素和可访问的 `aria-label`。
