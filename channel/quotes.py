import aiohttp
import asyncio
import json
import random
from datetime import datetime, timedelta
from pyrogram.enums import ParseMode  # Corrected import

from app import BOT, bot, Message

# ✅ CONFIG SECTION
YOUR_CHANNEL_ID = -1002665845048   # Replace with your target channel ID
YOUR_USERNAME = "TheQuotesFeed"         # Without @
CACHE_CHAT_ID = -1002852357421     # Chat ID of the cache message
CACHE_MSG_ID = 4                   # Message ID of the cache
ZEN_QUOTES_API = "https://zenquotes.io/api/random"
REQUEST_COOLDOWN = 32  # Cooldown between requests (seconds)


@bot.add_cmd(cmd="quotes")
async def schedule_quotes(bot: BOT, message: Message):
    args = message.text.strip().split()
    if len(args) != 2 or not args[1].isdigit():
        return await message.reply("Usage: .quotes <number_of_quotes>")

    count = int(args[1])
    await message.reply(f"Scheduling {count} quotes...")

    # Step 1: Load existing scheduled dates
    cache_msg = await bot.get_messages(chat_id=CACHE_CHAT_ID, message_ids=CACHE_MSG_ID)
    try:
        existing_dates = json.loads(cache_msg.text)
    except Exception as e:
        return await message.reply(f"❌ Failed to parse cache: {e}")

    existing_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in existing_dates if d.strip()]
    existing_dates_set = set(existing_dates)

    # Step 2: Determine next available dates
    if existing_dates:
        start_date = max(existing_dates) + timedelta(days=1)
    else:
        start_date = datetime.now().date() + timedelta(days=1)

    new_dates = []
    current_date = start_date

    while len(new_dates) < count:
        if current_date not in existing_dates_set:
            new_dates.append(current_date)
        current_date += timedelta(days=1)

    scheduled_dates = []

    # Step 3: Fetch and schedule quotes
    for date in new_dates:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ZEN_QUOTES_API) as resp:
                    quote_data = await resp.json()
                    await asyncio.sleep(REQUEST_COOLDOWN)  # Apply cooldown between requests

            quote = quote_data[0]["q"]
            author = quote_data[0]["a"]

            text = (
                f"<b>Quote of the day:</b>\n\n"
                f"<b>{quote}</b>\n"
                f"by <i>{author}</i>\n\n"
                f"<i>Follow @{YOUR_USERNAME} for more!</i>"
            )

            rand_hour = random.randint(8, 20)
            rand_minute = random.randint(0, 59)
            schedule_datetime = datetime.combine(date, datetime.min.time()).replace(
                hour=rand_hour, minute=rand_minute
            )

            await bot.send_message(
                chat_id=YOUR_CHANNEL_ID,
                text=text,
                parse_mode=ParseMode.HTML,  # Corrected usage of ParseMode.HTML
                schedule_date=schedule_datetime,
            )

            scheduled_dates.append(date.strftime("%Y-%m-%d"))

        except Exception as e:
            await message.reply(f"❌ Failed to schedule quote for {date}: {e}")
            continue

    # Step 4: Update cache message only if there's a new change
    updated_cache = existing_dates + [datetime.strptime(d, "%Y-%m-%d").date() for d in scheduled_dates]
    updated_cache = sorted(set(updated_cache))
    updated_cache_strings = [d.strftime("%Y-%m-%d") for d in updated_cache]

    # Only update the cache if there's an actual change
    if updated_cache_strings != json.loads(cache_msg.text):
        try:
            await bot.edit_message_text(
                chat_id=CACHE_CHAT_ID,
                message_id=CACHE_MSG_ID,
                text=json.dumps(updated_cache_strings, indent=2)
            )
        except Exception as e:
            return await message.reply(f"✅ Quotes scheduled, but failed to update cache: {e}")
    else:
        await message.reply("✅ Quotes scheduled, but no change to cache.")

    await message.reply("✅ Quotes scheduled successfully!")
