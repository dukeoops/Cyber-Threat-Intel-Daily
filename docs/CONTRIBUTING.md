# 贡献指南

感谢你对 **Cyber Threat Intel Daily** 的关注！欢迎以下各种形式的贡献：

## 如何贡献

### 报告问题

- 在 [Issues](../../issues) 页面提交 Bug 报告
- 请描述：操作系统、Python 版本、复现步骤、实际/预期结果

### 建议新功能

- 新的情报源（RSS URL）
- 新的情报分类关键词
- HTML 模板改进
- 邮件发送方式支持（如 SendGrid、AWS SES）

### 提交代码

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/add-new-source`
3. 提交修改：`git commit -m 'feat: add XYZ RSS source'`
4. 推送分支：`git push origin feat/add-new-source`
5. 发起 Pull Request

## 代码规范

- Python 代码遵循 PEP 8
- 函数需有简短 docstring 说明用途
- 新增 RSS 源请同步更新 `references/data_sources.md`
- 不要将 `config.json` 或含有个人信息的文件提交到仓库

## 常见贡献场景

### 添加新 RSS 源

1. 在 `scripts/fetch_intel.py` 的 `RSS_SOURCES` 字典中添加
2. 在 `references/data_sources.md` 中补充来源说明
3. 测试：`python3 scripts/fetch_intel.py --output /tmp/test.json`

### 添加情报分类关键词

在 `scripts/generate_report.py` 的 `CATEGORIES` 字典中对应分类下添加关键词。

### 改进 HTML 模板

`scripts/md_to_html.py` 中的 `CSS` 变量包含所有样式，`build_full_html()` 函数控制整体布局。

## 行为准则

- 保持友善、包容的社区氛围
- 技术讨论以事实为依据
- 不发布任何违法内容或恶意代码

---

*感谢每一位贡献者让这个项目变得更好！*
