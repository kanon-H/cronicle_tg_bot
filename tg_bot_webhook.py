#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import logging
import json
from typing import Dict, Any, List, Optional, Tuple

from dotenv import load_dotenv
import yaml
import httpx
# 导入telegram相关模块
from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommandScopeDefault,
    CallbackQuery
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Application
)

# 导入版本信息
try:
    from version import __version__
except ImportError:
    __version__ = "unknown"

# Ensure dependencies are installed:
# pip install python-telegram-bot python-dotenv pyyaml httpx

# Ensure we're using python-telegram-bot v20+ with proper imports

# ================== 配置加载 ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# 核心配置
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ALLOWED_USER_IDS = {
    int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x
}
ACTIONS_FILE = os.environ.get("ACTIONS_FILE", os.path.join(BASE_DIR, "actions.yaml"))
API_BASE_URL = os.environ.get("API_BASE_URL", "http://192.168.0.3:3012").rstrip("/")
API_KEY = os.environ.get("API_KEY", "")

# Webhook 配置
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "yourdomain.com").strip()
WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", "8443"))
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", f"/webhook/{BOT_TOKEN}").strip()

# 日志配置
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nas-bot-webhook")

# ================== 动作配置加载 ==================
def load_actions(path: str) -> Dict[str, Any]:
    """加载并验证 actions.yaml"""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "categories" not in data or not isinstance(data["categories"], list):
        raise ValueError("actions.yaml 格式错误：缺少 categories 列表")
    return data

ACTIONS = load_actions(ACTIONS_FILE)

# ================== 工具函数 ==================
def truncate(text: str, limit: int = 3000) -> str:
    """截断过长文本"""
    return text if len(text) <= limit else text[:limit] + "\n...（已截断）"

def user_allowed(update: Update) -> bool:
    """检查用户权限"""
    uid = update.effective_user.id if update.effective_user else None
    return uid in ALLOWED_USER_IDS

async def api_run_event(event_id: str) -> Dict[str, Any]:
    """调用NAS API"""
    url = f"{API_BASE_URL}/api/app/run_event/v1?api_key={API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json={"id": event_id})
            return {
                "ok": resp.is_success,
                "status_code": resp.status_code,
                "text": resp.text,
                "data": resp.json() if resp.headers.get("content-type") == "application/json" else {}
            }
    except httpx.TimeoutException:
        logger.error(f"API调用超时: {url}")
        return {
            "ok": False,
            "status_code": 0,
            "text": "API请求超时，请检查NAS服务是否可用",
            "data": {}
        }
    except httpx.NetworkError as e:
        logger.error(f"网络错误: {str(e)}")
        return {
            "ok": False,
            "status_code": 0,
            "text": f"网络连接错误: {str(e)}",
            "data": {}
        }
    except Exception as e:
        logger.error(f"API调用异常: {str(e)}")
        return {
            "ok": False,
            "status_code": 0,
            "text": f"API调用异常: {str(e)}",
            "data": {}
        }

# ================== Webhook 管理函数 ==================
async def setup_webhook(application: Application) -> None:
    """设置Telegram Webhook"""
    webhook_url = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}{WEBHOOK_PATH}"
    
    # 设置Webhook
    await application.bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True
    )
    logger.info(f"Webhook 已设置: {webhook_url}")

async def remove_webhook(application: Application) -> None:
    """移除Telegram Webhook"""
    await application.bot.delete_webhook()
    logger.info("Webhook 已移除")

# ================== 命令生成 ==================
def generate_bot_commands(actions_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """生成合法的Telegram命令列表"""
    commands = []
    used_cmds = set()
    
    for category in actions_data.get("categories", []):
        for action in category.get("actions", []):
            # 优先使用yaml中定义的command，否则从title生成
            raw_cmd = action.get("command", action["title"])
            cmd = re.sub(r"[^a-z0-9_]", "", str(raw_cmd).lower().strip())
            cmd = cmd[:32] or f"cmd_{len(used_cmds)}"  # 保证非空且不超过32字符
            
            # 确保命令唯一
            while cmd in used_cmds:
                cmd = f"{cmd}_{len(used_cmds)}"
            used_cmds.add(cmd)
            
            desc = f"{category['name']}: {action['title']}"[:256]  # 描述最长256字符
            commands.append((cmd, desc))
    
    # 添加固定命令
    commands.extend([
        ("start", "打开控制菜单"),
        ("help", "查看使用帮助"),
        ("status", "检查机器人状态"),
        ("webhook_status", "查看Webhook状态"),
        ("version", "查看当前版本")
    ])
    
    return commands

BOT_COMMANDS = generate_bot_commands(ACTIONS)

# ================== 键盘构建 ==================
def build_categories_keyboard() -> InlineKeyboardMarkup:
    """构建分类键盘"""
    buttons = []
    for idx, cat in enumerate(ACTIONS["categories"]):
        buttons.append([InlineKeyboardButton(cat["name"], callback_data=f"cat:{idx}")])
    return InlineKeyboardMarkup(buttons)

# ================== 处理器 ==================
async def register_commands(app: Application):
    """注册命令到Telegram菜单"""
    await app.bot.set_my_commands(
        commands=[BotCommand(cmd, desc) for cmd, desc in BOT_COMMANDS],
        scope=BotCommandScopeDefault()
    )
    logger.info(f"命令注册成功: {BOT_COMMANDS}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/start命令"""
    if not user_allowed(update):
        await update.message.reply_text("⛔ 无权限")
        return
    await update.message.reply_text(
        "请选择操作：\n• 直接输入命令如 /start_monitor\n• 或点击下方菜单",
        reply_markup=build_categories_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/help命令"""
    await update.message.reply_text(
        "可用命令：\n" + "\n".join(f"/{cmd} - {desc}" for cmd, desc in BOT_COMMANDS)
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/status命令"""
    await update.message.reply_text("✅ 服务运行正常")

async def webhook_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/webhook_status命令"""
    if not user_allowed(update):
        await update.message.reply_text("⛔ 无权限")
        return
    
    webhook_info = await context.bot.get_webhook_info()
    status = (
        f"Webhook 状态:\n"
        f"• URL: {webhook_info.url or '未设置'}\n"
        f"• 自定义证书: {'是' if webhook_info.has_custom_certificate else '否'}\n"
        f"• 待处理更新: {webhook_info.pending_update_count}\n"
        f"• 最后错误: {webhook_info.last_error_message or '无'}"
    )
    await update.message.reply_text(status)

async def dynamic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """动态处理所有注册的命令"""
    if not user_allowed(update):
        return
    
    command = update.message.text[1:].split("@")[0]  # 提取命令名
    for cat_idx, category in enumerate(ACTIONS["categories"]):
        for act_idx, action in enumerate(category["actions"]):
            # 匹配yaml中的command或生成的标准化命令
            expected_cmd = action.get("command", action["title"])
            expected_cmd = re.sub(r"[^a-z0-9_]", "", str(expected_cmd).lower())
            if command == expected_cmd:
                # 创建一个模拟的CallbackQuery对象
                from telegram import CallbackQuery
                import uuid
                
                # 构造CallbackQuery需要的数据
                callback_data = f"act:{cat_idx}:{act_idx}"
                
                # 创建一个假的callback_query对象来传递给button_router
                fake_callback_query = CallbackQuery(
                    id=str(uuid.uuid4()), 
                    from_user=update.effective_user, 
                    chat_instance=str(update.effective_chat.id), 
                    data=callback_data
                )
                # 关联bot到fake_callback_query对象
                fake_callback_query.set_bot(context.bot)
                
                # 创建一个新的Update对象，包含fake_callback_query
                fake_update = Update(
                    update_id=update.update_id,
                    callback_query=fake_callback_query
                )
                
                await button_router(fake_update, context)
                return
    
    await update.message.reply_text("⚠️ 未找到该命令，请输入 /help 查看可用命令")

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    query = update.callback_query
    await query.answer()
    
    if not user_allowed(update):
        await query.edit_message_text("⛔ 无权限")
        return

    data = query.data
    if data == "back":
        await query.edit_message_text("请选择分类：", reply_markup=build_categories_keyboard())
    elif data.startswith("cat:"):
        cat_idx = int(data.split(":")[1])
        cat = ACTIONS["categories"][cat_idx]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(action["title"], callback_data=f"act:{cat_idx}:{idx}")]
            for idx, action in enumerate(cat["actions"])
        ] + [[InlineKeyboardButton("⬅ 返回", callback_data="back")]])
        await query.edit_message_text(f"分类：{cat['name']}", reply_markup=keyboard)
    elif data.startswith("act:"):
        parts = data.split(":")
        cat_idx, act_idx = int(parts[1]), int(parts[2])
        cat = ACTIONS["categories"][cat_idx]
        act = cat["actions"][act_idx]
        title = act.get("title", "未命名动作")
        event_id = act.get("event_id", "")
        
        if not event_id:
            await query.edit_message_text("❗ 缺少event_id配置")
            return

        # 二次确认
        if act.get("confirm", False) and (len(parts) < 4 or parts[3] != "ok"):
            confirm_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 确认执行", callback_data=f"act:{cat_idx}:{act_idx}:ok")],
                [InlineKeyboardButton("❌ 取消", callback_data=f"cat:{cat_idx}")]
            ])
            await query.edit_message_text(f"确认执行：{title}？", reply_markup=confirm_kb)
            return

        # 执行动作
        await query.edit_message_text(f"🔄 正在执行: {title}...")
        try:
            result = await api_run_event(event_id)
            response = (
                f"✅ 成功执行: *{title}*\n"
                f"状态码: {result['status_code']}\n"
                f"响应: \n```\n{truncate(result['text'], 3000)}\n```"
            ) if result["ok"] else (
                f"❌ 执行失败: *{title}*\n"
                f"状态码: {result['status_code']}\n"
                f"错误: \n```\n{truncate(result['text'], 3000)}\n```"
            )
            await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"执行失败: {str(e)}")
            await query.edit_message_text(f"❌ 执行异常: {str(e)}")

async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/version命令"""
    await update.message.reply_text(f"当前版本: {__version__}")

# ================== 健康检查 ==================
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthCheckHandler(BaseHTTPRequestHandler):
    """健康检查处理器"""
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server(port=8080):
    """启动健康检查服务器"""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"健康检查服务已启动在端口 {port}")
    return server

# ================== 主程序 ==================
def main():
    logger.info("启动NAS控制机器人(Webhook模式)...")
    
    # 启动健康检查服务
    health_server = start_health_server()
    
    # 创建应用
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(register_commands)
        .post_shutdown(remove_webhook)
        .build()
    )

    # 注册处理器
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("webhook_status", webhook_status))
    app.add_handler(CommandHandler("version", version_command))

    # 动态注册所有命令
    for cmd, _ in [x for x in BOT_COMMANDS if x[0] not in ["start", "help", "status", "webhook_status"]]:
        app.add_handler(CommandHandler(cmd, dynamic_command))

    app.add_handler(CallbackQueryHandler(button_router))
    
    # 启动Webhook
    # 检查WEBHOOK_HOST是否为默认值或localhost/127.0.0.1
    if WEBHOOK_HOST in ['yourdomain.com', 'localhost', '127.0.0.1']:
        logger.warning("WEBHOOK_HOST设置为本地地址，这在生产环境中可能无法工作。请设置为公网IP或域名。")
        logger.info("启动轮询模式代替Webhook模式...")
        app.run_polling(drop_pending_updates=True)
    else:
        logger.info(f"启动Webhook模式，地址: {WEBHOOK_HOST}")
        app.run_webhook(
            listen="0.0.0.0",
            port=WEBHOOK_PORT,
            webhook_url=f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}{WEBHOOK_PATH}",
            url_path=WEBHOOK_PATH,
            drop_pending_updates=True
        )

if __name__ == "__main__":
    main()