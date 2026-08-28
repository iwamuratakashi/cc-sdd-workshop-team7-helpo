"""local-user-authentication — import 時に AuthRouter を共有レジストリへ登録する。"""
from app.auth.router import router as auth_router
from app.router_registry import router_registry

router_registry.register_router(auth_router)
