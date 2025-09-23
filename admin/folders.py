import asyncio
from asyncio import sleep
from pyrogram import raw, types, utils
from pyrogram.enums import ChatType
from ub_core import BOT, Message, bot
from app import CustomDB

# Database collections
ADM_CHAT_DB = CustomDB["adm_chat"]
EXC_CHAT_DB = CustomDB["exc_chat"]

async def get_folder() -> raw.types.DialogFilter | int:
    """Get existing Admin Chats folder or find available folder ID"""
    dialog_filters: raw.types.messages.DialogFilters = await bot.invoke(
        raw.functions.messages.GetDialogFilters()
    )
    folder_ids = set()
    for filter in dialog_filters.filters:
        if not isinstance(filter, raw.types.DialogFilter | raw.types.DialogFilterChatlist):
            continue
        if filter.title.text == "Admin Chats":
            return filter
        folder_ids.add(filter.id)

    # Find available folder ID
    for i in range(2, 256):
        if i not in folder_ids:
            return i
    else:
        raise ValueError("No Folder ID available.")

async def update_folder(
    folder_id,
    included_peers: list = None,
    excluded_peers: list = None,
    pinned_peers: list = None,
    folder=None,
) -> bool:
    """Update or create Admin Chats folder"""
    filter = folder or raw.types.DialogFilter(
        id=folder_id,
        title=raw.types.TextWithEntities(text="Admin Chats", entities=[]),
        pinned_peers=[] if pinned_peers is None else pinned_peers,
        include_peers=[] if included_peers is None else included_peers,
        exclude_peers=[] if excluded_peers is None else excluded_peers,
    )
    return await bot.invoke(
        raw.functions.messages.UpdateDialogFilter(
            id=folder_id,
            filter=filter,
        )
    )

async def get_dialogs():
    """Get all dialogs/chats"""
    current = 0
    total = (1 << 31) - 1
    request_limit = min(100, total)
    offset_date = 0
    offset_id = 0
    offset_peer = raw.types.InputPeerEmpty()
    seen_dialog_ids = set()

    while True:
        r = await bot.invoke(
            raw.functions.messages.GetDialogs(
                offset_date=offset_date,
                offset_id=offset_id,
                offset_peer=offset_peer,
                limit=request_limit,
                hash=0,
                exclude_pinned=False,
                folder_id=0,
            ),
            sleep_threshold=60,
        )

        users = {i.id: i for i in r.users}
        chats = {i.id: i for i in r.chats}
        messages = {}

        for message in r.messages:
            if isinstance(message, raw.types.MessageEmpty):
                continue
            chat_id = utils.get_peer_id(message.peer_id)
            messages[chat_id] = message

        dialogs = []
        for dialog in r.dialogs:
            if not isinstance(dialog, raw.types.Dialog):
                continue
            parsed = types.Dialog._parse(bot, dialog, messages, users, chats)
            if parsed is None:
                continue
            if parsed.chat is None:
                continue
            if parsed.chat.id in seen_dialog_ids:
                continue
            seen_dialog_ids.add(parsed.chat.id)
            dialogs.append(parsed)

        if not dialogs:
            return

        last = dialogs[-1]
        if last.top_message is None:
            return

        offset_id = last.top_message.id
        offset_date = last.top_message.date
        offset_peer = await bot.resolve_peer(last.chat.id)

        for dialog in dialogs:
            await sleep(0)
            yield dialog
            current += 1
            if current >= total:
                return

async def is_admin_group(chat) -> bool:
    """Check if chat is a group where user has admin privileges"""
    return (
        chat.admin_privileges and
        chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and
        not chat.type == ChatType.CHANNEL
    )

async def get_excluded_chats() -> set:
    """Get all excluded chat IDs from database"""
    excluded_chats = set()
    async for exc_chat in EXC_CHAT_DB.find():
        excluded_chats.add(exc_chat["_id"])
    return excluded_chats

@bot.add_cmd(cmd="folder")
async def create_admin_folder(bot: BOT, message: Message):
    """
    CMD: FOLDER
    INFO: Creates/updates Admin Chats folder with admin groups
    USAGE: .folder
    """
    resp = await message.reply("`Creating Admin Chats folder...`")

    try:
        folder = await get_folder()
        included_peers = []
        excluded_peers = []
        pinned_peers = []

        if isinstance(folder, raw.types.DialogFilter):
            included_peers.extend(folder.include_peers)
            excluded_peers.extend(folder.exclude_peers)
            pinned_peers.extend(folder.pinned_peers)
            folder_id = folder.id
        else:
            folder_id = folder

        # Get excluded chats from database
        excluded_chat_ids = await get_excluded_chats()

        # Clear existing admin chats from database
        await ADM_CHAT_DB.drop()

        existing_hashes = {x.access_hash for x in [*included_peers, *excluded_peers, *pinned_peers]}

        await resp.edit("`Scanning for admin groups...`")

        new_added = 0
        total_admin_groups = 0

        async for d in get_dialogs():
            # Skip if not an admin group
            if not await is_admin_group(d.chat):
                continue

            total_admin_groups += 1

            # Skip if chat is excluded
            if d.chat.id in excluded_chat_ids:
                continue

            # Skip if already in folder
            if d.chat._raw.access_hash in existing_hashes:
                # Add to database anyway for tracking
                await ADM_CHAT_DB.add_data({
                    "_id": d.chat.id,
                    "name": d.chat.title,
                    "type": str(d.chat.type)
                })
                continue

            # Add to folder and database
            peer = await bot.resolve_peer(d.chat.id)
            included_peers.append(peer)

            await ADM_CHAT_DB.add_data({
                "_id": d.chat.id,
                "name": d.chat.title,
                "type": str(d.chat.type)
            })

            new_added += 1

        # Update folder
        success = await update_folder(folder_id, included_peers, excluded_peers, pinned_peers)

        excluded_count = len(excluded_chat_ids)
        total_in_folder = len(included_peers)

        resp_text = (
            f"📁 <b>Admin Chats Folder {'Updated' if success else 'Failed'}</b>\n\n"
            f"<b>Total Admin Groups:</b> {total_admin_groups}\n"
            f"<b>In Folder:</b> {total_in_folder}\n"
            f"<b>Excluded:</b> {excluded_count}\n"
            f"<b>New Added:</b> {new_added}"
        )

        await resp.edit(resp_text)
        await bot.log_text(text=resp_text, type="info")

    except Exception as e:
        await resp.edit(f"❌ Error: {str(e)}")
        await bot.log_text(text=f"Error in folder command: {str(e)}", type="error")

@bot.add_cmd(cmd="exc")
async def exclude_chat(bot: BOT, message: Message):
    """
    CMD: EXC
    INFO: Exclude current chat from Admin Chats folder (silent operation)
    USAGE: .exc
    """
    chat_id = message.chat.id
    chat_title = message.chat.title or "Unknown"

    try:
        # Add to excluded chats database
        await EXC_CHAT_DB.add_data({
            "_id": chat_id,
            "name": chat_title,
            "type": str(message.chat.type)
        })

        # Remove from admin chats database if exists
        await ADM_CHAT_DB.delete_data(id=chat_id)

        # Get current folder and remove this chat
        folder = await get_folder()
        if isinstance(folder, raw.types.DialogFilter):
            # Remove from included peers
            current_peer = await bot.resolve_peer(chat_id)
            folder.include_peers = [
                peer for peer in folder.include_peers
                if peer.access_hash != current_peer.access_hash
            ]

            # Update folder
            await update_folder(folder_id=folder.id, folder=folder)

        # Log the action (no reply to keep it silent)
        log_text = f"🚫 Excluded chat: {chat_title} ({chat_id}) from Admin Chats folder"
        await bot.log_text(text=log_text, type="info")

    except Exception as e:
        # Silent fail, only log the error
        await bot.log_text(text=f"Error in exc command: {str(e)}", type="error")

@bot.add_cmd(cmd="reload")
async def reload_admin_folder(bot: BOT, message: Message):
    """
    CMD: RELOAD
    INFO: Refresh Admin Chats folder - add new admin groups, remove non-admin groups
    USAGE: .reload
    """
    resp = await message.reply("`Reloading Admin Chats folder...`")

    try:
        folder = await get_folder()
        if not isinstance(folder, raw.types.DialogFilter):
            await resp.edit("❌ Admin Chats folder not found. Use .folder to create it first.")
            return

        await resp.edit("`Checking current admin status...`")

        # Get excluded chats
        excluded_chat_ids = await get_excluded_chats()

        # Check current chats in folder for admin status
        to_remove = []
        current_peers = folder.include_peers.copy()

        for peer in current_peers:
            try:
                # Get chat info
                chat_info = await bot.get_chat(peer.channel_id if hasattr(peer, 'channel_id') else peer.user_id)

                # Remove if no longer admin or is excluded
                if not await is_admin_group(chat_info) or chat_info.id in excluded_chat_ids:
                    to_remove.append(peer)
                    await ADM_CHAT_DB.delete_data(id=chat_info.id)
            except:
                # If can't get chat info, remove it
                to_remove.append(peer)

        # Remove non-admin chats from folder
        for peer in to_remove:
            folder.include_peers.remove(peer)

        await resp.edit("`Scanning for new admin groups...`")

        # Find new admin groups
        existing_hashes = {x.access_hash for x in folder.include_peers}
        new_added = 0

        async for d in get_dialogs():
            if not await is_admin_group(d.chat):
                continue

            if d.chat.id in excluded_chat_ids:
                continue

            if d.chat._raw.access_hash not in existing_hashes:
                peer = await bot.resolve_peer(d.chat.id)
                folder.include_peers.append(peer)

                await ADM_CHAT_DB.add_data({
                    "_id": d.chat.id,
                    "name": d.chat.title,
                    "type": str(d.chat.type)
                })

                new_added += 1

        # Update folder
        success = await update_folder(folder_id=folder.id, folder=folder)

        resp_text = (
            f"🔄 <b>Admin Chats Folder {'Reloaded' if success else 'Failed'}</b>\n\n"
            f"<b>Removed:</b> {len(to_remove)} (no longer admin/excluded)\n"
            f"<b>Added:</b> {new_added} (new admin groups)\n"
            f"<b>Total in Folder:</b> {len(folder.include_peers)}\n"
            f"<b>Excluded:</b> {len(excluded_chat_ids)}"
        )

        await resp.edit(resp_text)
        await bot.log_text(text=resp_text, type="info")

    except Exception as e:
        await resp.edit(f"❌ Error: {str(e)}")
        await bot.log_text(text=f"Error in reload command: {str(e)}", type="error")

# Additional utility command to view current status
@bot.add_cmd(cmd="admstatus")
async def admin_status(bot: BOT, message: Message):
    """
    CMD: ADMSTATUS
    INFO: Show current admin folder status
    USAGE: .admstatus
    """
    try:
        # Count admin chats in database
        admin_count = await ADM_CHAT_DB.count_documents({})
        excluded_count = await EXC_CHAT_DB.count_documents({})

        # Get folder info
        folder = await get_folder()
        folder_status = "Found" if isinstance(folder, raw.types.DialogFilter) else "Not Found"
        folder_count = len(folder.include_peers) if isinstance(folder, raw.types.DialogFilter) else 0

        status_text = (
            f"📊 <b>Admin Folder Status</b>\n\n"
            f"<b>Folder:</b> {folder_status}\n"
            f"<b>Chats in Folder:</b> {folder_count}\n"
            f"<b>Admin Chats in DB:</b> {admin_count}\n"
            f"<b>Excluded Chats:</b> {excluded_count}"
        )

        await message.reply(status_text, del_in=15)

    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}", del_in=10)
