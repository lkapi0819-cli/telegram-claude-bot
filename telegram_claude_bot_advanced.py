  import os
  import logging
  from dotenv import load_dotenv
  from telegram import Update
  from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
  import anthropic

  load_dotenv()
  logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
  logger = logging.getLogger(__name__)

  TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
  ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
  CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
  MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

  if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
      raise ValueError("请设置环境变量")

  claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
  conversation_history = {}
  SYSTEM_PROMPT = "你是一个友好、有帮助的AI助手。用中文简洁回复，可以使用emoji。"

  async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
      await update.message.reply_html(f"👋 你好 {update.effective_user.mention_html()}！我是 Claude AI 助手。\n\n命令：/start /clear /help
  /info")

  async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
      user_id = update.effective_user.id
      conversation_history[user_id] = []
      await update.message.reply_text("✅ 历史已清空")

  async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
      await update.message.reply_text("📖 命令：/start /clear /info /help")

  async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
      user_id = update.effective_user.id
      history = conversation_history.get(user_id, [])
      await update.message.reply_text(f"📊 消息数: {len(history)}\n模型: {CLAUDE_MODEL}")

  async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
      user_id = update.effective_user.id
      user_message = update.message.text

      if user_id not in conversation_history:
          conversation_history[user_id] = []

      conversation_history[user_id].append({"role": "user", "content": user_message})

      try:
          response = claude_client.messages.create(
              model=CLAUDE_MODEL,
              max_tokens=MAX_TOKENS,
              system=SYSTEM_PROMPT,
              messages=conversation_history[user_id]
          )

          for block in response.content:
              if block.type == "text":
                  conversation_history[user_id].append({"role": "assistant", "content": block.text})

                  if len(block.text) > 4096:
                      for i in range(0, len(block.text), 4096):
                          await update.message.reply_text(block.text[i:i+4096])
                  else:
                      await update.message.reply_text(block.text)
                  break
      except Exception as e:
          logger.error(f"Error: {e}")
          await update.message.reply_text("❌ 发生错误，请重试")

  def main():
      application = Application.builder().token(TELEGRAM_TOKEN).build()
      application.add_handler(CommandHandler("start", start))
      application.add_handler(CommandHandler("clear", clear))
      application.add_handler(CommandHandler("help", help_cmd))
      application.add_handler(CommandHandler("info", info))
      application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
      logger.info("Bot 启动中...")
      application.run_polling()

  if __name__ == "__main__":
      main()
