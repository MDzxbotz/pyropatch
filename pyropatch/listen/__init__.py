from pyrogram.types import Update

from .update import *
from .message import *
from .callback import *
from .inline_query import *
from .inline_result import *

import pyrogram
from ..utils import patch2, patchable


async def temp(_: Client, update: Update):
    update.stop_propagation()


@patch2(pyrogram.client.Client)
class Client(Client):
    @patchable
    def __init__(self, *args, **kwargs):
        self.cbd_listeners = {}
        self.msg_listeners = {}
        self.inline_listeners = {}
        self.result_listeners = {}
        self.update_listeners = {}
        self.old2___init__(*args, **kwargs)

    @patchable
    async def start(self, *args, **kwargs):
        await self._initialize_pyropatch()
        await self.old2_start(*args, **kwargs)

    @patchable
    async def _initialize_pyropatch(self):
        for handler in pyropatch_handlers[-100]:
            self.add_handler(handler, group=-100)
       
pyropatch_handlers = {
    -100: [
        pyrogram.handlers.MessageHandler(temp, checker=True),
        pyrogram.handlers.CallbackQueryHandler(temp, checker=True),
        pyrogram.handlers.CallbackQueryHandler(temp, checker=True),
        pyrogram.handlers.ChosenInlineResultHandler(temp, checker=True)
    ]
}
        
