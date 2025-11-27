from app import BOT, bot, Message


@bot.add_cmd(cmd="pin")
async def pin_cmd(bot: BOT, message: Message):
    """
    CMD: PIN
    INFO: Pin a replied message.
    FLAGS: -loud / -notify to send notification.
    USAGE:
        .pin
        .pin loud
        .pin -loud
        .pin notify
        .pin -notify
    """
    if not message.replied:
        await message.reply("Reply to a message to pin it.", del_in=5)
        return

    # Original logic:
    # notify = not any(arg in args for arg in ('loud', 'notify'))
    # and then: pin(disable_notification=notify)
    # -> default: silent pin; with 'loud'/'notify': send notification

    full_text = (message.text or "").lower()

    # Support both styles: ".pin loud" and ".pin -loud"
    is_loud = any(
        key in full_text
        for key in (" loud", " notify", "-loud", "-notify")
    )

    # disable_notification=True -> silent
    # disable_notification=False -> with notification
    disable_notification = not is_loud

    try:
        await message.replied.pin(disable_notification=disable_notification)
        if disable_notification:
            await message.reply("Pinned (silent).", del_in=5)
        else:
            await message.reply("Pinned (with notification).", del_in=5)
    except Exception as e:
        await message.reply(
            f"Failed to pin message.\n<b>Reason:</b> <code>{e}</code>",
            del_in=8,
        )


@bot.add_cmd(cmd="unpin")
async def unpin_cmd(bot: BOT, message: Message):
    """
    CMD: UNPIN
    INFO: Unpin a replied message.
    USAGE:
        .unpin (reply to a pinned message)
    """
    if not message.replied:
        await message.reply("Reply to a pinned message to unpin it.", del_in=5)
        return

    try:
        await message.replied.unpin()
        await message.reply("Unpinned.", del_in=5)
    except Exception as e:
        await message.reply(
            f"Failed to unpin message.\n<b>Reason:</b> <code>{e}</code>",
            del_in=8,
        )
