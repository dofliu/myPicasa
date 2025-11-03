#!/bin/bash
# MediaToolkit MCP Server 啟動腳本

echo "🚀 啟動 MediaToolkit MCP Server..."
echo "📋 確保已安裝所需套件："
echo "   pip install mcp Pillow pypdf docx2pdf pdf2docx reportlab"
echo ""
echo "⚙️  配置 Claude Desktop:"
echo "   編輯 claude_desktop_config.json"
echo "   添加 media-toolkit server 配置"
echo ""
echo "▶️  啟動中..."

cd "$(dirname "$0")/.."
python -m mcp_server.server
