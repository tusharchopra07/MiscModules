# Made by @wwhyafk

from app import BOT, bot, Message

async def _list_dialogs(bot: BOT, message: Message, chat_type: str):
    """
    chat_type = "SUPERGROUP" or "CHANNEL"
    """
    response_lines = []
    count = 0

    async for dialog in bot.client.get_dialogs():
        chat = dialog.chat
        if chat_type in str(chat.type):
            count += 1
            name = getattr(chat, "title", "Unknown")
            chat_id = chat.id
            username = getattr(chat, "username", None)

            if username:
                link = f"https://t.me/{username}"
            else:
                link = f"tg://openmessage?chat_id={chat_id}"

            response_lines.append(
                f"**Name:** {name}\n**ID:** `{chat_id}`\n**Link:** {link}\n"
            )

    if count == 0:
        await message.reply(f"⚠️ No {chat_type.lower()}s found.")
        return

    result = "\n".join(response_lines)
    filename = f"{chat_type.lower()}s.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(result)

    await message.reply_document(filename, caption=f"📜 Found {count} {chat_type.lower()}s.")

@bot.add_cmd(cmd="listchannels")
async def list_channels(bot: BOT, message: Message):
    await message.reply("🔍 Fetching channels... please wait.")
    await _list_dialogs(bot, message, chat_type="CHANNEL")

@bot.add_cmd(cmd="listgroups")
async def list_groups(bot: BOT, message: Message):
    await message.reply("🔍 Fetching groups... please wait.")
    await _list_dialogs(bot, message, chat_type="SUPERGROUP")
