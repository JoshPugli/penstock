"""User-facing decorators: @entrypoint, @step."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from penstock._config import get_backend
from penstock._context import (
    FlowContext,
    _reset_context,
    _set_context,
    get_flow_context,
)
from penstock._registry import _registry
from penstock._types import P, R, StepInfo

# ---------------------------------------------------------------------------
# after= normalization
# ---------------------------------------------------------------------------


def _normalize_after(
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None,
) -> tuple[str, ...]:
    if after is None:
        return ()
    if isinstance(after, str):
        return (after,)
    if callable(after):
        return (after.__name__,)
    result: list[str] = []
    for item in after:
        if isinstance(item, str):
            result.append(item)
        else:
            result.append(item.__name__)
    return tuple(result)


# ---------------------------------------------------------------------------
# @entrypoint("flow_name")
# ---------------------------------------------------------------------------


def entrypoint(
    flow_name: str,
    *,
    name: str | None = None,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Mark a callable as a flow entrypoint.

    Always called with parentheses: ``@entrypoint("my_flow")``.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        return _make_entrypoint(fn, flow_name=flow_name, name=name, after=after)

    return decorator


def _make_entrypoint(
    fn: Callable[..., Any],
    *,
    flow_name: str,
    name: str | None,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None,
) -> Callable[..., Any]:
    step_name = name or fn.__name__
    after_tuple = _normalize_after(after)

    info = StepInfo(
        name=step_name,
        flow_name=flow_name,
        after=after_tuple,
        is_entrypoint=True,
    )
    _registry.register(info)

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _set_context(FlowContext())
            backend = get_backend()
            try:
                with backend.span(step_name, flow_name):
                    return await fn(*args, **kwargs)
            finally:
                _reset_context()

        return async_wrapper

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        _set_context(FlowContext())
        backend = get_backend()
        try:
            with backend.span(step_name, flow_name):
                return fn(*args, **kwargs)
        finally:
            _reset_context()

    return wrapper


# ---------------------------------------------------------------------------
# @step("flow_name")
# ---------------------------------------------------------------------------


def step(
    flow_name: str,
    *,
    name: str | None = None,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Mark a callable as a flow step.

    Always called with parentheses: ``@step("my_flow", after="validate")``.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        return _make_step(fn, flow_name=flow_name, name=name, after=after)

    return decorator


def _make_step(
    fn: Callable[..., Any],
    *,
    flow_name: str,
    name: str | None,
    after: str | Callable[..., Any] | list[str | Callable[..., Any]] | None,
) -> Callable[..., Any]:
    step_name = name or fn.__name__
    after_tuple = _normalize_after(after)

    info = StepInfo(
        name=step_name,
        flow_name=flow_name,
        after=after_tuple,
        is_entrypoint=False,
    )
    _registry.register(info)

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = get_flow_context()
            if ctx is None:
                raise RuntimeError(
                    f"@step '{step_name}' called outside of a flow context. "
                    "Ensure an @entrypoint has been called first."
                )
            backend = get_backend()
            with backend.span(step_name, flow_name):
                return await fn(*args, **kwargs)

        return async_wrapper

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = get_flow_context()
        if ctx is None:
            raise RuntimeError(
                f"@step '{step_name}' called outside of a flow context. "
                "Ensure an @entrypoint has been called first."
            )
        backend = get_backend()
        with backend.span(step_name, flow_name):
            return fn(*args, **kwargs)

    return wrapper
