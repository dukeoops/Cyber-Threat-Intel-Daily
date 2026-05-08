# 🔴 Cyber Threat Intel Daily

> 自动化网络安全威胁情报日报系统 — 从数据采集到邮件发送，全流程一键执行

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)]()

---

## 简介

**Cyber Threat Intel Daily** 是一个开箱即用的网络安全威胁情报日报自动化框架，帮助安全团队每日汇聚来自全球 13+ 权威安全媒体的最新情报，结合 AI 分析，生成结构化的专业日报并通过邮件分发。

**核心特性：**

- 📡 **多源情报采集** — 13 个 RSS 源（FreeBuf、看雪、CISA、Krebs、Dark Reading 等）+ 0.zone 勒索情报
- 🤖 **AI 驱动分析** — 与 AI 助手（WorkBuddy/Claude/GPT 等）集成，以情报分析专家视角撰写日报
- 🏷️ **自动分类标注** — 漏洞、勒索、APT、数据泄露、供应链等 7 大类自动分类
- 📧 **精美 HTML 邮件** — 红色主题卡片布局，CVE 高亮徽章，自动生成目录，支持打印导出 PDF
- ⚙️ **零外部依赖** — 仅使用 Python 3.8+ 标准库，无需安装第三方包（邮件发送使用标准 SMTP）
- 🔧 **高度可配置** — 通过 `config.json` 配置邮件、自定义 RSS 源、输出路径

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/cyber-threat-intel-daily.git
cd cyber-threat-intel-daily
```

### 2. 配置

```bash
cp config.example.json config.json
# 编辑 config.json，填写你的 SMTP 邮件配置和收件人
```

### 3. 采集今日情报

```bash
python3 scripts/fetch_intel.py --output output/intel_raw.json
```

### 4. 生成结构化上下文

```bash
python3 scripts/generate_report.py output/intel_raw.json --output output/intel_context.md
```

### 5. AI 生成日报（核心步骤）

将 `output/intel_context.md` 的内容提供给你的 AI 助手，并附上以下指令：

> 请以网络安全情报分析专家的视角，基于以下原始情报数据，
> 参考 `references/report_template.md` 的格式规范，
> 生成一份专业的网络安全威胁情报日报（中文，Markdown 格式）。

将 AI 输出保存为 `output/威胁情报日报_YYYYMMDD.md`。

### 6. 转换 HTML 并发送邮件

```bash
# 转换为 HTML
python3 scripts/md_to_html.py output/威胁情报日报_20260508.md \
  --output output/威胁情报日报_20260508.html

# 发送邮件（需配置 config.json）
python3 scripts/send_report.py \
  --report output/威胁情报日报_20260508.md \
  --html output/威胁情报日报_20260508.html \
  --config config.json
```

### 一键运行（自动化模式）

```bash
bash scripts/run_daily.sh
```

---

## 项目结构

```
cyber-threat-intel-daily/
├── scripts/
│   ├── fetch_intel.py       # Phase 1：情报采集（RSS + 0.zone）
│   ├── generate_report.py   # Phase 2：结构化上下文生成
│   ├── md_to_html.py        # Phase 3：Markdown → 精美 HTML
│   ├── send_report.py       # Phase 4：SMTP 邮件发送
│   └── run_daily.sh         # 全流程一键脚本
├── references/
│   ├── report_template.md   # 日报格式规范与写作指南
│   └── data_sources.md      # 数据源说明与注意事项
├── output/                  # 生成物输出目录（gitignored）
├── config.example.json      # 配置模板（复制为 config.json 后使用）
├── .gitignore
├── LICENSE
└── README.md
```

---

## 数据源

### RSS 源（13 个）

| 来源 | 语言 | 类型 |
|------|------|------|
| FreeBuf | 中文 | 综合安全媒体 |
| 看雪论坛 | 中文 | 逆向/漏洞技术 |
| 安全圈 | 中文 | 行业资讯聚合 |
| 嗅学安全 | 中文 | 威胁分析 |
| Krebs on Security | 英文 | 知名安全调查博客 |
| Dark Reading | 英文 | 企业安全媒体 |
| CISA | 英文 | 美国官方网络安全机构 |
| Threatpost | 英文 | 安全新闻 |
| Schneier on Security | 英文 | 安全专家博客 |
| Ars Technica Security | 英文 | 科技媒体安全栏目 |
| The Register | 英文 | 科技新闻 |
| Wired Security | 英文 | 主流科技媒体 |
| Microsoft Security Blog | 英文 | 厂商官方博客 |

### 专项情报源

- **0.zone 勒索情报** — 全球勒索软件受害者追踪、被盗数据公告

---

## 日报格式

AI 生成的日报包含以下章节：

1. **执行摘要** — 3-5 句话概括当日最重要威胁
2. **威胁态势评级** — 🔴高 / 🟠中高 / 🟡中 / 🟢低
3. **高优先级威胁预警** — 最紧迫漏洞/攻击事件
4. **漏洞与补丁情报** — CVE 表格 + 重点分析
5. **勒索软件与 APT 活动** — 受害者表格 + 组织追踪
6. **数据泄露与隐私安全**
7. **供应链与软件安全**
8. **政策监管与执法动态**
9. **防御建议摘要** — 立即行动 / 近期跟进 / 持续监控
10. **情报来源统计**

---

## 配置说明

### config.json

```json
{
  "email": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_use_tls": true,
    "smtp_user": "sender@example.com",
    "smtp_password": "your-password",
    "sender_name": "CTI Daily Report",
    "recipients": ["security-team@example.com"]
  },
  "report": {
    "output_dir": "./output",
    "title": "网络安全威胁情报日报"
  },
  "sources": {
    "rss_enabled": true,
    "ransomware_intel_enabled": true,
    "custom_rss_feeds": [
      {"name": "自定义源", "url": "https://example.com/feed.xml"}
    ]
  }
}
```

### 常用邮件服务 SMTP 配置

| 服务 | smtp_host | smtp_port | 备注 |
|------|-----------|-----------|------|
| Gmail | smtp.gmail.com | 587 | 需开启应用专用密码 |
| QQ 邮箱 | smtp.qq.com | 587 | 需开启 SMTP 并获取授权码 |
| 163 邮箱 | smtp.163.com | 587 | 需开启 SMTP |
| Outlook | smtp-mail.outlook.com | 587 | |
| 企业自建 | 填实际地址 | 填实际端口 | |

---

## 定时运行

### Linux/macOS（crontab）

```bash
# 每天早上 8 点运行
0 8 * * * cd /path/to/cyber-threat-intel-daily && bash scripts/run_daily.sh >> logs/cron.log 2>&1
```

### 与 WorkBuddy 集成

如果你使用 [WorkBuddy](https://www.codebuddy.cn)，可以将本项目作为 Skill 集成，通过 AI 对话触发全流程，无需手动执行命令。

---

## 注意事项

- **网络访问**：部分英文 RSS 源（如 Wired、Cloudflare 防护站点）在国内可能需要代理
- **0.zone 爬取**：为动态渲染页面，依赖正则提取，页面结构变化时需更新解析逻辑
- **微信 RSS 源**：通过第三方转换服务（wechat2rss.xlab.app），存在失效风险，失效时自动跳过
- **日期过滤**：文章按发布时间过滤，允许 ±1 天误差（兼容时区差异）
- **隐私**：`config.json` 包含 SMTP 密码，已加入 `.gitignore`，请勿提交到公开仓库

---

## 贡献

欢迎提交 Issue 和 Pull Request！请参阅 [CONTRIBUTING.md](docs/CONTRIBUTING.md)。

## 许可证

[MIT License](LICENSE) — 可自由使用、修改和分发。

---

*TLP: WHITE — 本项目可自由分享*
