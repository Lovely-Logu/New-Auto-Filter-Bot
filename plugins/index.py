
import logging

import asyncio

from pyrogram import Client, filters, enums

from pyrogram.errors import FloodWait

from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified

from info import ADMINS

from info import INDEX_REQ_CHANNEL as LOG_CHANNEL

from database.ia_filterdb import save_file

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils import temp

import re

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)

lock = asyncio.Lock()


@Client.on_callback_query(filters.regex(r'^index'))

async def index_files(bot, query):

    if query.data.startswith('index_cancel'):

        temp.CANCEL = True

        return await query.answer("Cancelling Indexing")

    _, raju, chat, lst_msg_id, from_user = query.data.split("#")

    if raju == 'reject':

        await query.message.delete()

        await bot.send_message(int(from_user),

                               f'Your Submission for indexing {chat} has been decliened by our moderators.',

                               reply_to_message_id=int(lst_msg_id))

        return



    if lock.locked():

        return await query.answer('Wait until previous process complete.', show_alert=True)

    msg = query.message



    await query.answer('Processing...⏳', show_alert=True)

    if int(from_user) not in ADMINS:

        await bot.send_message(int(from_user),

                               f'Your Submission for indexing {chat} has been accepted by our moderators and will be added soon.',

                               reply_to_message_id=int(lst_msg_id))

    await msg.edit(

        "Starting Indexing",

        reply_markup=InlineKeyboardMarkup(

            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]

        )

    )

    try:

        chat = int(chat)

    except:

        chat = chat

    await index_files_to_db(int(lst_msg_id), chat, msg, bot)





@Client.on_message((filters.forwarded | (filters.regex("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")) & filters.text ) & filters.private & filters.incoming)

async def send_for_index(bot, message):

    if message.text:

        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")

        match = regex.match(message.text)

        if not match:

            return await message.reply('Invalid link')

        chat_id = match.group(4)

        last_msg_id = int(match.group(5))

        if chat_id.isnumeric():

            chat_id  = int(("-100" + chat_id))

    elif message.forward_from_chat.type == enums.ChatType.CHANNEL:

        last_msg_id = message.forward_from_message_id

        chat_id = message.forward_from_chat.username or message.forward_from_chat.id

    else:

        return

    try:

        await bot.get_chat(chat_id)

    except ChannelInvalid:

        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')

    except (UsernameInvalid, UsernameNotModified):

        return await message.reply('Invalid Link specified.')

    except Exception as e:

        logger.exception(e)

        return await message.reply(f'Errors - {e}')

    try:

        k = await bot.get_messages(chat_id, last_msg_id)

    except:

        return await message.reply('Make Sure That Iam An Admin In The Channel, if channel is private')

    if k.empty:

        return await message.reply('This may be group and iam not a admin of the group.')



    if message.from_user.id in ADMINS:

        buttons = [

            [

                InlineKeyboardButton('Yes',

                                     callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')

            ],

            [

                InlineKeyboardButton('close', callback_data='close_data'),

            ]

        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        return await message.reply(

            f'Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>',

            reply_markup=reply_markup)



    if type(chat_id) is int:

        try:

            link = (await bot.create_chat_invite_link(chat_id)).invite_link

        except ChatAdminRequired:

            return await message.reply('Make sure iam an admin in the chat and have permission to invite users.')

    else:

        link = f"@{message.forward_from_chat.username}"

    buttons = [

        [

            InlineKeyboardButton('Accept Index',

                                 callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')

        ],

        [

            InlineKeyboardButton('Reject Index',

                                 callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'),

        ]

    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    await bot.send_message(LOG_CHANNEL,

                           f'#IndexRequest\n\nBy : {message.from_user.mention} (<code>{message.from_user.id}</code>)\nChat ID/ Username - <code> {chat_id}</code>\nLast Message ID - <code>{last_msg_id}</code>\nInviteLink - {link}',

                           reply_markup=reply_markup)

    await message.reply('ThankYou For the Contribution, Wait For My Moderators to verify the files.')


lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    _, ident, chat, lst_msg_id, skip = query.data.split("#")
    if ident == 'yes':
        msg = query.message
        await msg.edit("Starting Indexing...")
        try:
            chat = int(chat)
        except:
            chat = chat
        await index_files_to_db(int(lst_msg_id), chat, msg, bot, int(skip))
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("Trying to cancel Indexing...")


@Client.on_message(filters.command('index') & filters.private & filters.incoming & filters.user(ADMINS))
async def send_for_index(bot, message):
    if lock.locked():
        return await message.reply('Wait until previous process complete.')
    i = await message.reply("Forward last message or send last message link.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await i.delete()
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            msg_link = msg.text.split("/")
            last_msg_id = int(msg_link[-1])
            chat_id = msg_link[-2]
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
        except:
            await message.reply('Invalid message link!')
            return
    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = msg.forward_from_message_id
        chat_id = msg.forward_from_chat.username or msg.forward_from_chat.id
    else:
        await message.reply('This is not forwarded message or link.')
        return
    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        return await message.reply(f'Errors - {e}')

    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("I can index only channels.")

    s = await message.reply("Send skip message number.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await s.delete()
    try:
        skip = int(msg.text)
    except:
        return await message.reply("Number is invalid.")

    buttons = [[
        InlineKeyboardButton('YES', callback_data=f'index#yes#{chat_id}#{last_msg_id}#{skip}')
    ],[
        InlineKeyboardButton('CLOSE', callback_data='close_data'),
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply(f'Do you want to index {chat.title} channel?\nTotal Messages: <code>{last_msg_id}</code>', reply_markup=reply_markup)


async def index_files_to_db(lst_msg_id, chat, msg, bot, skip):
    start_time = time.time()
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    current = skip
    
    async with lock:
        try:
            async for message in bot.iter_messages(chat, lst_msg_id, skip):
                time_taken = get_readable_time(time.time()-start_time)
                if temp.CANCEL:
                    temp.CANCEL = False
                    await msg.edit(f"Successfully Cancelled!\nCompleted in {time_taken}\n\nSaved <code>{total_files}</code> files to Database!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>")
                    return
                current += 1
                if current % 30 == 0:
                    btn = [[
                        InlineKeyboardButton('CANCEL', callback_data=f'index#cancel#{chat}#{lst_msg_id}#{skip}')
                    ]]
                    await msg.edit_text(text=f"Total messages received: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>", reply_markup=InlineKeyboardMarkup(btn))
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                elif not (str(media.file_name).lower()).endswith(tuple(INDEX_EXTENSIONS)):
                    unsupported += 1
                    continue
                media.caption = message.caption
                sts = await save_file(media)
                if sts == 'suc':
                    total_files += 1
                elif sts == 'dup':
                    duplicate += 1
                elif sts == 'err':
                    errors += 1
        except Exception as e:
            await msg.reply(f'Index canceled due to Error - {e}')
        else:
            await msg.edit(f'Succesfully saved <code>{total_files}</code> to Database!\nCompleted in {time_taken}\n\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>')
