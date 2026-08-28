"""ai-helpdesk-chat — import 時に ChatRouter を共有レジストリへ登録する。"""
from app.chat.router import router as chat_router
from app.router_registry import router_registry

router_registry.register_router(chat_router)
