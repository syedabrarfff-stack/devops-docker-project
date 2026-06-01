from __future__ import annotations

from contextvars import ContextVar, Token


_current_tenant_id: ContextVar[str | None] = ContextVar(
    "current_tenant_id",
    default=None,
)


def set_current_tenant_id(tenant_id: str | None) -> Token[str | None]:
    return _current_tenant_id.set(tenant_id)


def get_current_tenant_id() -> str | None:
    return _current_tenant_id.get()


def reset_current_tenant_id(token: Token[str | None]) -> None:
    _current_tenant_id.reset(token)
