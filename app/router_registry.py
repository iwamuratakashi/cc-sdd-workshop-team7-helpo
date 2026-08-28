from fastapi import APIRouter, FastAPI


class RouterRegistry:
    def __init__(self):
        self._routers: list[tuple[APIRouter, str, list[str] | None]] = []

    def register_router(
        self,
        router: APIRouter,
        prefix: str = "",
        tags: list[str] | None = None,
    ) -> None:
        self._routers.append((router, prefix, tags))


def include_registered_routers(app: FastAPI, registry: RouterRegistry) -> None:
    for router, prefix, tags in registry._routers:
        app.include_router(router, prefix=prefix, tags=tags)


# 下位機能が import 時に自らのルーターを登録するための共有インスタンス
router_registry = RouterRegistry()
