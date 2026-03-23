"""
Telegram Bot 集成 Claude API - 增强版
功能：环境变量配置、更好的错误处理、多用户支持
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 从环境变量读取配置
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

# 验证配置
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN 环境变量未设置")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY 环境变量未设置")

# 初始化Claude客户端
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# 存储每个用户的对话历史
conversation_history = {}

# 系统提示词
SYSTEM_PROMPT = """你是一个友好、有帮助的AI助手。你会用简洁、清晰的方式回答问题。

注意事项：
- 用中文回复（除非用户使用其他语言）
- 保持回答简洁，一般不超过500字
- 如果问题复杂，可以分点说明
- 使用emoji让回复更友好"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /start 命令"""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 你好 {user.mention_html()}！\n\n"
        f"我是由 Claude 驱动的 AI 助手。\n"
        f"🤖 模型: {CLAUDE_MODEL}\n"
        f"💬 直接发送消息即可开始对话。\n\n"
        f"✨ 命令列表：\n"
        f"/start - 开始对话\n"
        f"/clear - 清空对话历史\n"
        f"/help - 查看帮助\n"
        f"/info - 查看当前会话信息"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /help 命令"""
    help_text = (
        "📖 帮助信息\n\n"
        "命令：\n"
        "/start - 开始对话\n"
        "/clear - 清空对话历史\n"
        "/info - 查看会话信息\n"
        "/help - 查看此帮助\n\n"
        "💡 提示：\n"
        "• 发送文字即可与Claude对话\n"
        "• 对话会在同一个会话中保持上下文\n"
        "• 使用 /clear 清空历史记录\n"
        "• 长消息会自动分片发送"
    )
    await update.message.reply_text(help_text)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """显示当前会话信息"""
    user_id = update.effective_user.id
    history = conversation_history.get(user_id, [])

    # 计算token数（粗略估计）
    total_chars = sum(len(msg.get("content", "")) for msg in history)
    estimated_tokens = total_chars // 4

    info_text = (
        f"📊 会话信息\n\n"
        f"• 对话轮数: {len(history) // 2}\n"
        f"• 消息数: {len(history)}\n"
        f"• 估计token数: ~{estimated_tokens}\n"
        f"• 模型: {CLAUDE_MODEL}\n"
        f"• 最大tokens: {MAX_TOKENS}"
    )
    await update.message.reply_text(info_text)


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """清空对话历史"""
    user_id = update.effective_user.id
    if user_id in conversation_history:
        conversation_history[user_id] = []
    await update.message.reply_text("✅ 对话历史已清空")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户消息"""
    user_id = update.effective_user.id
    user_message = update.message.text

    # 显示"正在输入"状态
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        # 初始化用户对话历史
        if user_id not in conversation_history:
            conversation_history[user_id] = []

        # 添加用户消息到历史
        conversation_history[user_id].append({
            "role": "user",
            "content": user_message
        })

        # 调用Claude API
        response = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=conversation_history[user_id]
        )

        # 提取Claude的回复
        assistant_message = None
        for block in response.content:
            if block.type == "text":
                assistant_message = block.text
                break

        if assistant_message:
            # 将助手回复添加到历史
            conversation_history[user_id].append({
                "role": "assistant",
                "content": assistant_message
            })

            # 发送回复（Telegram消息长度限制为4096字符）
            if len(assistant_message) > 4096:
                # 分批发送长消息
                for i in range(0, len(assistant_message), 4096):
                    await update.message.reply_text(assistant_message[i:i+4096])
            else:
                await update.message.reply_text(assistant_message)

            # 记录使用情况
            logger.info(
                f"用户 {user_id} - "
                f"输入: {response.usage.input_tokens} tokens, "
                f"输出: {response.usage.output_tokens} tokens"
            )

        else:
            await update.message.reply_text("❌ 抱歉，我无法生成回复。")

    except anthropic.RateLimitError as e:
        logger.error(f"速率限制错误: {e}")
        await update.message.reply_text("⚠️ 请求过于频繁，请稍后再试。")
    except anthropic.AuthenticationError:
        logger.error("API认证失败")
        await update.message.reply_text("❌ API认证失败，请检查配置。")
    except anthropic.APIStatusError as e:
        logger.error(f"API错误: {e}")
        await update.message.reply_text(f"❌ API错误: {e.message}")
    except Exception as e:
        logger.error(f"处理消息时出错: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 发生错误，请稍后重试。")


def main() -> None:
    """启动Bot"""
    logger.info(f"启动 Telegram Claude Bot (模型: {CLAUDE_MODEL})")

    # 创建应用
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 注册命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("info", info))

    # 注册消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 启动Bot
    logger.info("Bot 启动中...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
