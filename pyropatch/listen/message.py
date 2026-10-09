# this code snippet is created using
# https://github.com/usernein/pyromod/blob/master/pyromod/listen/listen.py

from ..utils import patch, patchable
import pyrogram
import asyncio
import functools

loop = asyncio.get_event_loop()


class ListenerCanceled(Exception):
    pass


pyrogram.errors.ListenerCanceled = ListenerCanceled


@patch(pyrogram.client.Client)
class Client():

    @patchable
    async def listen_message(self, chat_id, filters=None, timeout=None):
        if type(chat_id) != int:
            chat = await self.get_chat(chat_id)
            chat_id = chat.id
        future = loop.create_future()
        future.add_done_callback(
            functools.partial(self.remove_message_listener, chat_id)
        )
        self.msg_listeners.update({
            chat_id: {"future": future, "filters": filters}
        })
        return await asyncio.wait_for(future, timeout)

    @patchable
    async def ask_message(self, chat_id, text, filters=None, timeout=None, *args, **kwargs):
        request = await self.send_message(chat_id, text, *args, **kwargs)
        response = await self.listen_message(chat_id, filters, timeout)
        response.request = request
        return response

    @patchable
    def remove_message_listener(self, chat_id, future):
        if (
            chat_id in self.msg_listeners
            and future == self.msg_listeners[chat_id]["future"]
        ): 
            self.msg_listeners.pop(chat_id)

    @patchable
    def cancel_message_listener(self, chat_id):
        listener = self.msg_listeners.get(chat_id)
        if not listener or listener['future'].done():
            return
        listener['future'].set_exception(ListenerCanceled())
        self.remove_message_listener(chat_id, listener['future'])

    @patchable
    def listen_messages(self, chat_id: int):
        return MessagePipe(chat_id, self.bulk_msg_listeners)
        

@patch(pyrogram.handlers.message_handler.MessageHandler)
class MessageHandler():
    @patchable
    def __init__(self, callback: callable, filters=None, checker=False):
        self.checker = checker
        self.user_callback = callback
        self.old___init__(self.resolve_listener, filters)

    @patchable
    async def resolve_listener(self, client, message, *args):
        
        if self.checker:
            chat_id = getattr(message.chat, "id", 0)

            bulk_msg_listener = client.bulk_msg_listeners.get(chat_id)
            if bulk_msg_listener:
               bulk_msg_listener.send(message)
               return await self.user_callback(client, message, *args)
             
            bulk_update_listener = client.bulk_update_listeners.get(chat_id)
            if bulk_update_listener:
                bulk_update_listener.send(message)
                return await self.user_callback(client, message, *args)
            
            update_listener = client.update_listeners.get(chat_id)
            if (
                update_listener
                and not update_listener["future"].done()
            ):
                update_listener['future'].set_result(message)
                return await self.user_callback(client, message, *args)
                
            listener = client.msg_listeners.get(chat_id)
            if listener and not listener['future'].done():
                if (
                    await listener['filters'](client, message) 
                    if callable(listener['filters']) 
                    else True
                ):
                    listener['future'].set_result(message)
                    await self.user_callback(client, message, *args)
        else:
            await self.user_callback(client, message, *args)

    @patchable
    async def check(self, client, update):
        if self.checker:
            chat_id = getattr(update.chat, "id", 0)

            if chat_id in client.bulk_msg_listeners:
               return True 

            elif chat_id in client.bulk_update_listeners:
               return True 
            
            update_listener = client.update_listeners.get(chat_id)
            if (
                update_listener
                and not update_listener["future"].done()
            ):
               return (
                   await update_listener["filters"](client, update)
                   if callable(update_listener["filters"]) else True
               )
               
            listener = client.msg_listeners.get(chat_id)
            if listener and not listener['future'].done():
                return await listener['filters'](client, update) if callable(listener['filters']) else True
        if callable(self.filters):
            return await self.filters(client, update)
        return True


class UpdatePipe:

    def __init__(self, id, listener_map: dict):
        self.chat_id = id
        self.listener_map = listener_map
        self.queue =  asyncio.Queue()
        self.initialize = False 

    async def __aenter__(self):
        self.initialize = True 
        self.listener_map[self.chat_id] = self
        return self 

    async def __aexit__(self, exc_type, exc, tb):
        self.initialize = False 
        self.listener_map.pop(self.chat_id, None)

    def __aiter__(self):
        return self 

    def send(self, item):
        self.queue.put_nowait(item)

    def empty(self):
        return self.queue.empty()

    def pause(self):
        del self.listener_map[self.chat_id]

    def resume(self):
        self.listener_map[self.chat_id] = self

    async def __anext__(self):
        if not self.initialize:
           raise Exception("Must be called inside an async context manager")
        return await self.queue.get() 
    
    async def listen(self):
        return await anext(self)

class MessagePipe(UpdatePipe):
    pass 
