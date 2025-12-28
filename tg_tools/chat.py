import os

from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import BadRequest, UserNotParticipant

from ub_core.utils import get_name
from app import BOT, Message


@BOT.add_cmd(cmd="ids")
async def get_ids(bot: BOT, message: Message) -> None:
    reply: Message = message.replied
    if reply:
        resp_str: str = ""

        reply_user, reply_forward = reply.forward_from_chat, reply.from_user

        resp_str += f"<b>{get_name(reply.chat)}</b>: <code>{reply.chat.id}</code>\n"

        if reply_forward:
            resp_str += f"<b>{get_name(reply_forward)}</b>: <code>{reply_forward.id}</code>\n"

        if reply_user:
            resp_str += f"<b>{get_name(reply_user)}</b>: <code>{reply_user.id}</code>"
    elif message.input:
        resp_str: int = (await bot.get_chat(message.input[1:])).id
    else:
        resp_str: str = f"<b>{get_name(message.chat)}</b>: <code>{message.chat.id}</code>"

    await message.reply(resp_str)


@BOT.add_cmd(cmd="join")
async def join_chat(bot: BOT, message: Message) -> None:
    chat: str = message.input
    try:
        await bot.join_chat(chat)
    except (KeyError, BadRequest):
        try:
            await bot.join_chat(os.path.basename(chat).strip())
        except Exception as e:
            await message.reply(str(e))
            return

    await message.reply("Joined")


@BOT.add_cmd(cmd="leave")
async def leave_chat(bot: BOT, message: Message) -> None:
    if message.input:
        chat = message.input
    else:
        chat = message.chat.id

    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat, me.id)

        # 🚫 BLOCK first – before countdown
        if member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            await message.reply("❌ Leave blocked: you are admin in this chat.")
            return

    except UserNotParticipant:
        pass
    except Exception:
        pass

    # Only show countdown if leaving is allowed
    if not message.input:
        await message.reply(
            text=f"Leaving current chat in 5 seconds...\nReply with `{message.trigger}c` to cancel.",
            del_in=5,
            block=True,
        )

    try:
        await bot.leave_chat(chat)
        await message.reply("✅ Left chat.")
    except (KeyError, BadRequest):
        try:
            await bot.leave_chat(os.path.basename(str(chat)).strip())
        except Exception as e:
            await message.reply(str(e))

    message.stop_propagation()

