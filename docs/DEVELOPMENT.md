# 开发者文档

## 架构概览

```
数据流：
  网络（RSS/0.zone）
       ↓
  fetch_intel.py         → intel_raw_YYYYMMDD.json
       ↓
  generate_report.py     → intel_context_YYYYMMDD.md（结构化上下文）
       ↓
  AI 分析（人工/自动）   → 威胁情报日报_YYYYMMDD.md（最终报告）
       ↓
  md_to_html.py          → 威胁情报日报_YYYYMMDD.html
       ↓
  send_report.py         → 邮件（HTML正文 + HTML附件）
```

## 各脚本说明

### fetch_intel.py

**职责**：从 RSS 和 0.zone 抓取当日原始情报

**输出格式（JSON）**：
```json
{
  "date": "20260508",
  "fetched_at": "2026-05-08T00:00:00+00:00",
  "rss_articles": [
    {
      "source": "FreeBuf",
      "title": "...",
      "link": "https://...",
      "pub_date": "2026-05-08T06:00:00+00:00",
      "summary": "..."
    }
  ],
  "ransomware_intel": [...],
  "stats": {
    "rss_count": 42,
    "ransomware_count": 8,
    "total": 50
  }
}
```

**扩展**：在 `RSS_SOURCES` 字典中添加新源即可自动采集。

---

### generate_report.py

**职责**：将原始 JSON 按情报类别整理为 Markdown 上下文文档

**分类逻辑**：`CATEGORIES` 字典定义关键词 → 分类映射，文章可属于多个分类。

**输出**：结构化 Markdown，包含分类章节和勒索情报，供 AI 分析使用。

---

### md_to_html.py

**职责**：将 Markdown 日报转换为完全独立的单文件 HTML

**特性**：
- 轻量级 Markdown 解析器（无第三方库）
- 支持：标题层级、表格、列表、代码块、引用块、内联格式
- CVE 编号自动高亮（黄色徽章）
- 威胁等级 emoji 转徽章组件
- 自动从 h2 标题生成目录导航
- 中文字体优先（PingFang SC / Microsoft YaHei）

---

### send_report.py

**职责**：通过标准 SMTP 发送 HTML 邮件（正文 + HTML 附件）

**邮件结构**：
```
MIMEMultipart/mixed
  ├── MIMEMultipart/alternative
  │     ├── text/plain（备用纯文本）
  │     └── text/html（精美 HTML 正文）
  └── text/html（HTML 报告附件）
```

---

## 测试各阶段

```bash
# 1. 测试采集（不写文件，输出到终端）
python3 scripts/fetch_intel.py --date $(date +%Y%m%d)

# 2. 管道模式：采集 → 上下文一步完成
python3 scripts/fetch_intel.py | python3 scripts/generate_report.py -

# 3. 测试 HTML 转换
python3 scripts/md_to_html.py output/报告.md --output /tmp/test.html

# 4. 测试 SMTP（发送至自己）
python3 scripts/send_report.py --report output/报告.md \
  --to me@example.com \
  --smtp-host smtp.example.com \
  --smtp-user me@example.com \
  --smtp-pass "xxx"
```

## 常见问题

### RSS 源返回 0 条

- 该源当日可能无更新，属正常现象
- 若长期为 0，可能该 RSS URL 已失效，需更新
- 微信 RSS 源（wechat2rss.xlab.app）有时会临时失效

### 0.zone 爬取失败

- 可能受地区网络限制，使用 `--no-ransomware` 参数跳过
- 页面结构更新后正则可能失效，需更新 `fetch_ransomware_intel()` 函数

### SMTP 发送失败

- Gmail：需在账户安全设置中生成「应用专用密码」
- 企业邮箱：确认 SMTP 服务已开启，检查防火墙是否放行 587 端口
- SSL 错误：尝试将 `smtp_use_tls: false`（使用 SSL 模式，端口通常为 465）
