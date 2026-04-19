"""Lightweight package init for analysis imports.

Keep CLI wiring out of module import so optimization scripts can import
`repro.config` and related helpers without pulling optional geo stacks.
"""

__all__: list[str] = []
