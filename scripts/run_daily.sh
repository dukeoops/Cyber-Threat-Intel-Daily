#!/bin/bash
# run_daily.sh — 威胁情报日报一键运行脚本
#
# 功能流程：
#   1. 采集情报（RSS + 0.zone）
#   2. 生成结构化上下文文档
#   3. （可选）调用本地/远程 AI 生成报告
#   4. 转换为 HTML
#   5. 发送邮件
#
# 用法：
#   bash run_daily.sh                    # 今日日报
#   bash run_daily.sh --date 20260508    # 指定日期
#   bash run_daily.sh --no-email         # 不发邮件，只生成文件
#
# 前置要求：
#   - Python 3.8+
#   - 复制并填写 config.json（参考 config.example.json）
#   - 若需发送邮件，需配置好 config.json 中的 email 字段

set -euo pipefail

# ─── 配置 ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config.json"
OUTPUT_DIR="${PROJECT_DIR}/output"

DATE_STR=$(date +%Y%m%d)
SEND_EMAIL=true

# ─── 参数解析 ─────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)      DATE_STR="$2"; shift 2 ;;
        --no-email)  SEND_EMAIL=false; shift ;;
        --output)    OUTPUT_DIR="$2"; shift 2 ;;
        --help|-h)
            echo "用法: bash run_daily.sh [--date YYYYMMDD] [--no-email] [--output DIR]"
            exit 0 ;;
        *) echo "[WARN] 未知参数: $1"; shift ;;
    esac
done

# ─── 初始化 ───────────────────────────────────────────────────────────────────
mkdir -p "$OUTPUT_DIR"

RAW_JSON="${OUTPUT_DIR}/intel_raw_${DATE_STR}.json"
CONTEXT_MD="${OUTPUT_DIR}/intel_context_${DATE_STR}.md"
REPORT_MD="${OUTPUT_DIR}/威胁情报日报_${DATE_STR}.md"
REPORT_HTML="${OUTPUT_DIR}/威胁情报日报_${DATE_STR}.html"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "开始生成威胁情报日报（日期：${DATE_STR}）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─── Phase 1：采集情报 ────────────────────────────────────────────────────────
log "[1/4] 采集情报数据..."

CONFIG_ARG=""
if [[ -f "$CONFIG_FILE" ]]; then
    CONFIG_ARG="--config ${CONFIG_FILE}"
fi

python3 "${SCRIPT_DIR}/fetch_intel.py" \
    --date "${DATE_STR}" \
    --output "${RAW_JSON}" \
    ${CONFIG_ARG} \
    2>&1

log "情报采集完成：${RAW_JSON}"

# ─── Phase 2：生成结构化上下文 ────────────────────────────────────────────────
log "[2/4] 生成结构化上下文..."

python3 "${SCRIPT_DIR}/generate_report.py" \
    "${RAW_JSON}" \
    --output "${CONTEXT_MD}"

log "上下文文档已生成：${CONTEXT_MD}"

# ─── Phase 3：生成 Markdown 报告 ─────────────────────────────────────────────
log "[3/4] 生成 Markdown 报告..."

# 这里提供两种方式：
#
# 方式 A（推荐）：通过 WorkBuddy / AI 工具读取 CONTEXT_MD，由 AI 生成最终报告
#   - 将 CONTEXT_MD 传给你使用的 AI 助手
#   - 让 AI 参考 references/ 目录下的模板生成报告
#   - 保存为 REPORT_MD
#
# 方式 B（简单模式）：直接将上下文文档重命名为报告
#   cp "${CONTEXT_MD}" "${REPORT_MD}"
#
# 以下为简单模式（如你集成了 AI，请替换此处逻辑）：
if [[ ! -f "${REPORT_MD}" ]]; then
    log "[INFO] 未检测到已生成的报告，将上下文文档用作报告（简单模式）"
    cp "${CONTEXT_MD}" "${REPORT_MD}"
    log "[INFO] 建议：将 ${CONTEXT_MD} 提供给 AI 助手生成专业报告，保存为 ${REPORT_MD}"
else
    log "报告文件已存在：${REPORT_MD}"
fi

# ─── Phase 4：转换 HTML ───────────────────────────────────────────────────────
log "[4/4] 转换为 HTML..."

if python3 "${SCRIPT_DIR}/md_to_html.py" "${REPORT_MD}" --output "${REPORT_HTML}"; then
    log "HTML 报告已生成：${REPORT_HTML}"
else
    log "[WARN] HTML 转换失败，将跳过 HTML 附件"
    REPORT_HTML=""
fi

# ─── Phase 5（可选）：发送邮件 ────────────────────────────────────────────────
if [[ "$SEND_EMAIL" == "true" ]]; then
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log "[WARN] 未找到 config.json，跳过邮件发送"
        log "       请复制 config.example.json 为 config.json 并填写邮件配置"
    else
        log "发送邮件..."
        HTML_ARG=""
        if [[ -n "$REPORT_HTML" && -f "$REPORT_HTML" ]]; then
            HTML_ARG="--html ${REPORT_HTML}"
        fi

        python3 "${SCRIPT_DIR}/send_report.py" \
            --report "${REPORT_MD}" \
            ${HTML_ARG} \
            --config "${CONFIG_FILE}" \
            && log "邮件发送成功" \
            || log "[WARN] 邮件发送失败，请检查 SMTP 配置"
    fi
else
    log "跳过邮件发送（--no-email）"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "完成！"
log "  上下文文档 : ${CONTEXT_MD}"
log "  Markdown报告: ${REPORT_MD}"
[[ -n "$REPORT_HTML" ]] && log "  HTML 报告  : ${REPORT_HTML}"
