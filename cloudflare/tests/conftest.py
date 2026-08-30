"""Compatibilidade mínima para importar o Worker no pytest CPython.

A produção roda em Pyodide/Cloudflare. Estes stubs só permitem importar módulos
para testes determinísticos de orquestração; rede e APIs reais continuam
proibidas para não criar falsos positivos de integração.
"""
from __future__ import annotations

import sys
import types


if "js" not in sys.modules:
    js = types.ModuleType("js")

    class _Object:
        @staticmethod
        def fromEntries(value):
            return value

    class _Uint8Array:
        @staticmethod
        def new(value):
            return value

    async def _fetch(*_args, **_kwargs):
        raise RuntimeError("fetch do runtime JS não deve ser chamado em testes determinísticos")

    js.Object = _Object
    js.Uint8Array = _Uint8Array
    js.fetch = _fetch
    sys.modules["js"] = js


if "pyodide" not in sys.modules:
    pyodide = types.ModuleType("pyodide")
    ffi = types.ModuleType("pyodide.ffi")

    def _to_js(value, **_kwargs):
        return value

    ffi.to_js = _to_js
    pyodide.ffi = ffi
    sys.modules["pyodide"] = pyodide
    sys.modules["pyodide.ffi"] = ffi


if "workers" not in sys.modules:
    workers = types.ModuleType("workers")

    class _Response:
        def __init__(self, body="", status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = headers or {}

    class _WorkerEntrypoint:
        pass

    class _DurableObject:
        def __init__(self, ctx=None, env=None):
            self.ctx = ctx
            self.env = env

    workers.Response = _Response
    workers.WorkerEntrypoint = _WorkerEntrypoint
    workers.DurableObject = _DurableObject
    sys.modules["workers"] = workers
