import asyncio
import pyrogram 
from functools import partial
from ..utils import patch, patchable

loop = asyncio.get_event_loop() 


@patch(pyrogram.client.Client)
class Client:
    
    @patchable 
    async def ask_update(self, chat_id, text, filters=None, timeout=None, *args, **kwargs):
        request = await self.send_message(
            chat_id=chat_id,
            text=text,
            *args,
            **kwargs
        )
        response = await self.listen_update(
            chat_id,
            request.id,
            filters=filters,
            timeout=timeout
        )
        response.request = request 
        return response
        
    @patchable
    async def listen_update(self, chat_id, message_id, filters=None, timeout=None):
        if isinstance(chat_id, str):
           chat_id = (await self.get_chat(chat_id)).id
           
        future = loop.create_future()
        future.add_done_callback(
            partial(self.remove_listener, chat_id)
        )
        self.update_listeners.update(
            {chat_id: {
                "future": future,
                "filters": filters,
                "message_id": message_id
            }
        })
        return await asyncio.wait_for(future, timeout=timeout)
        
    @patchable
    def remove_listener(self, future, chat_id):
        data = self.update_listeners.get(chat_id)
        if (
            data is not None 
            and data["future"] == future
        ):  
            self.update_listeners.pop(chat_id)