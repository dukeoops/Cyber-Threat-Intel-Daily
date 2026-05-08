#!/usr/bin/env python3
"""
send_report.py - 通用邮件发送脚本（SMTP）

将威胁情报日报（Markdown + HTML）通过 SMTP 发送给收件人。
支持配置文件驱动，无需修改代码。

用法：
  # 使用配置文件发送
  python3 send_report.py --report report.md --html report.html --config config.json

  # 命令行参数覆盖
  python3 send_report.py --report report.md --to security@example.com \\
    --smtp-host smtp.example.com --smtp-user user@example.com --smtp-pass "xxx"

依赖：Python 3.8+ 标准库（smtplib, email）
"""

import argparse
import base64
import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


# ─── 默认邮件正文模板 ─────────────────────────────────────────────────────────

def build_html_body(context_snippet: str, date_str: str) -> str:
    """构建 HTML 邮件正文"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei',
         'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto;
         padding: 20px; background: #f5f5f5; }}
  .header {{ background: linear-gradient(135deg, #c0392b, #8e1a12); color: white;
             border-radius: 12px; padding: 25px 30px; margin-bottom: 20px; }}
  .header h1 {{ margin: 0 0 8px 0; font-size: 22px; }}
  .header .meta {{ opacity: 0.9; font-size: 13px; display: flex; gap: 16px; flex-wrap: wrap; }}
  .tlp {{ background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.4);
          padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
  .card {{ background: white; border-radius: 12px; padding: 24px;
           margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .tip {{ background: #fffbeb; border: 1px solid #fde68a;
          border-left: 4px solid #f59e0b; padding: 12px 16px;
          border-radius: 0 8px 8px 0; margin-bottom: 20px; font-size: 13px; color: #92400e; }}
  .content-box {{ background: #f9fafb; border-radius: 8px; padding: 15px;
                  white-space: pre-wrap; font-size: 13px; line-height: 1.65;
                  color: #374151; max-height: 400px; overflow-y: auto; }}
  h2 {{ color: #1f2937; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-top: 0; }}
  .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>

<div class="header">
  <h1>🔴 网络安全威胁情报日报</h1>
  <div class="meta">
    <span>📅 {date_str}</span>
    <span class="tlp">TLP: WHITE</span>
    <span>⏱ {datetime.now().strftime('%H:%M')} 生成</span>
  </div>
</div>

<div class="tip">
  📎 <strong>本邮件附有完整 HTML 格式报告</strong>，含目录导航、CVE 高亮、完整表格。
  请下载附件并在浏览器中打开查阅。
</div>

<div class="card">
  <h2>📊 今日情报摘要（节选）</h2>
  <div class="content-box">{context_snippet[:3000]}</div>
  <p style="color: #6b7280; margin-top: 12px; font-size: 12px;">
    * 完整报告请查看邮件附件 HTML 文件
  </p>
</div>

<div class="footer">
  <p>TLP: WHITE — 本报告可自由分享</p>
  <p>数据来源：自动化抓取 + AI 分析整合 | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
</body>
</html>"""


def load_config(config_path: str) -> dict:
    """加载 config.json，返回邮件相关配置"""
    path = os.path.expanduser(config_path)
    if not os.path.exists(path):
        print(f"[ERROR] 配置文件不存在：{path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def send_via_smtp(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    use_tls: bool,
    sender_name: str,
    recipients: list,
    subject: str,
    html_body: str,
    text_body: str,
    attachment_path: str = None,
):
    """通过标准 SMTP 发送邮件（支持 HTML 正文 + 附件）"""
    msg = MIMEMultipart("mixed")
    msg["From"]    = f"{sender_name} <{smtp_user}>"
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = subject

    # 正文（HTML + 纯文本备用）
    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText(text_body, "plain", "utf-8"))
    body_part.attach(MIMEText(html_body, "html",  "utf-8"))
    msg.attach(body_part)

    # HTML 附件
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            att_data = f.read()
        att = MIMEBase("text", "html")
        att.set_payload(att_data)
        encoders.encode_base64(att)
        att_name = os.path.basename(attachment_path)
        att.add_header("Content-Disposition", "attachment", filename=att_name)
        att.add_header("Content-Type", "text/html; charset=utf-8")
        msg.attach(att)
        print(f"[INFO] 附件：{att_name}（{len(att_data):,} bytes）")
    else:
        print("[WARN] 未找到 HTML 附件，将不附带附件发送", file=sys.stderr)

    # 发送
    try:
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.ehlo()
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipients, msg.as_bytes())
        server.quit()
        print(f"[OK] 邮件发送成功！")
        print(f"     收件人: {', '.join(recipients)}")
        print(f"     主题  : {subject}")
    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="通过 SMTP 发送威胁情报日报",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 使用配置文件
  python3 send_report.py --report report.md --html report.html --config config.json

  # 纯命令行参数
  python3 send_report.py --report report.md --html report.html \\
    --to security@example.com \\
    --smtp-host smtp.gmail.com --smtp-port 587 \\
    --smtp-user you@gmail.com --smtp-pass "app-password"
        """
    )
    parser.add_argument("--report", required=True, help="Markdown 报告文件路径（用于提取摘要）")
    parser.add_argument("--html",   default=None,  help="HTML 报告文件路径（作为附件发送）")
    parser.add_argument("--config", default=None,  help="config.json 路径")
    parser.add_argument("--to",     nargs="+",     help="收件人邮箱（可多个）")
    parser.add_argument("--smtp-host",   default=None)
    parser.add_argument("--smtp-port",   type=int, default=587)
    parser.add_argument("--smtp-user",   default=None)
    parser.add_argument("--smtp-pass",   default=None)
    parser.add_argument("--sender-name", default="CTI Daily Report")
    parser.add_argument("--no-tls",      action="store_true", help="使用 SSL 而非 STARTTLS")
    args = parser.parse_args()

    # 优先用配置文件，命令行参数可覆盖
    cfg_email = {}
    if args.config:
        cfg = load_config(args.config)
        cfg_email = cfg.get("email", {})

    smtp_host  = args.smtp_host  or cfg_email.get("smtp_host")
    smtp_port  = args.smtp_port  or cfg_email.get("smtp_port", 587)
    smtp_user  = args.smtp_user  or cfg_email.get("smtp_user")
    smtp_pass  = args.smtp_pass  or cfg_email.get("smtp_password")
    use_tls    = (not args.no_tls) and cfg_email.get("smtp_use_tls", True)
    sender     = args.sender_name or cfg_email.get("sender_name", "CTI Daily")
    recipients = args.to          or cfg_email.get("recipients", [])

    if not smtp_host or not smtp_user or not smtp_pass:
        print("[ERROR] 缺少 SMTP 配置，请使用 --config 或命令行参数提供", file=sys.stderr)
        sys.exit(1)
    if not recipients:
        print("[ERROR] 未指定收件人，请使用 --to 或在 config.json 中配置", file=sys.stderr)
        sys.exit(1)

    # 读取报告内容（用于邮件正文摘要）
    report_path = os.path.expanduser(args.report)
    if not os.path.exists(report_path):
        print(f"[ERROR] 报告文件不存在：{report_path}", file=sys.stderr)
        sys.exit(1)
    report_md = Path(report_path).read_text(encoding="utf-8")

    # 构建日期字符串
    date_cn = datetime.now().strftime("%Y年%m月%d日")

    # 构建邮件正文
    html_body = build_html_body(report_md[:3000], date_cn)
    text_body = f"网络安全威胁情报日报 {date_cn}\n\n" + report_md[:2000]

    subject = f"🔴 网络安全威胁情报日报 | {datetime.now().strftime('%Y-%m-%d')}"

    send_via_smtp(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_pass,
        use_tls=use_tls,
        sender_name=sender,
        recipients=recipients,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        attachment_path=os.path.expanduser(args.html) if args.html else None,
    )


if __name__ == "__main__":
    main()
