# message_processor.py
from handlers import handle_incoming_message

def process_message(chat_id, text):
    # تمرير الرسالة مباشرة للملف الجديد
    handle_incoming_message(chat_id, text)
