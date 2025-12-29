from app import BOT, bot, Message, Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import re


def is_authorized(user_id: int) -> bool:
    return user_id in [Config.OWNER_ID, *Config.SUDO_USERS]


@bot.add_cmd(cmd=["buttons"])
async def edit_channel_post(bot: BOT, message: Message):
    """
    CMD: BUTTONS
    INFO: Add buttons to an existing channel post.
    ACCESS: Owner & Sudo only
    """

    # 🚫 Block everyone except owner & sudo
    if not message.from_user or not is_authorized(message.from_user.id):
        return

    if not message.text:
        return

    if not (message.text.startswith(".buttons") or message.text.startswith("?buttons")):
        return

    try:
        lines = message.text.split("\n")
        if len(lines) < 2:
            await message.reply("❌ Usage: `.buttons <channel_id>/<message_id>` OR `.buttons <post_url>` followed by buttons.")
            return

        post_reference = lines[0].split(" ", 1)[1].strip()

        match = re.search(r"(?:https://t\.me/(c/)?([\w\d_]+)/(\d+))", post_reference)
        if match:
            is_private = match.group(1) == "c/"
            channel_ref = match.group(2)
            message_id = int(match.group(3))

            if is_private:
                channel_id = int(f"-100{channel_ref}")
            else:
                chat = await bot.get_chat(channel_ref)
                channel_id = chat.id
        else:
            if "/" not in post_reference:
                await message.reply("❌ Invalid format.")
                return

            channel_id, message_id = post_reference.split("/")
            channel_id = int(channel_id)
            message_id = int(message_id)

        await bot.get_chat(channel_id)

        button_lines = lines[1:]
        keyboard = []
        current_row = []

        for line in button_lines:
            parts = line.split(" - ", 1)
            if len(parts) != 2:
                continue

            text = parts[0].strip()
            url_parts = parts[1].split(":same")
            url = url_parts[0].strip()
            same_line = len(url_parts) > 1

            btn = InlineKeyboardButton(text, url=url)

            if same_line:
                current_row.append(btn)
            else:
                if current_row:
                    keyboard.append(current_row)
                current_row = [btn]

        if current_row:
            keyboard.append(current_row)

        markup = InlineKeyboardMarkup(keyboard)

        old_msg = await bot.get_messages(channel_id, message_id)
        if old_msg.reply_markup == markup:
            await message.reply("⚠️ Same buttons already exist.")
            return

        await bot.edit_message_reply_markup(channel_id, message_id, reply_markup=markup)
        await message.reply("✅ Buttons added successfully!")

    except Exception as e:
        await message.reply(f"❌ Error: {e}")
