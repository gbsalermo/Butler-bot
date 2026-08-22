"""Compatibilidade mínima para importar o Worker no pytest CPython.

O código de produção roda em Pyodide e recebe os módulos ``js`` e
``pyodide.ffi`` do runtime Cloudflare. A suíte determinística não faz chamadas
HTTP reais; ela só precisa conseguir importar os módulos que contêm as funções
puras testadas.
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
