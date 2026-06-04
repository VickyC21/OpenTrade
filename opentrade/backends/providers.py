"""Compatibility exports for modularized provider implementations."""

from __future__ import annotations

from opentrade.backends import provider_akshare as _provider_akshare
from opentrade.backends import provider_efinance as _provider_efinance
from opentrade.backends import provider_yfinance as _provider_yfinance
from opentrade.backends import providers_common as _providers_common

for _module in (_providers_common, _provider_efinance, _provider_akshare, _provider_yfinance):
    for _name, _value in vars(_module).items():
        if _name.startswith('__'):
            continue
        globals()[_name] = _value

del _module
del _name
del _value


def __dir__() -> list[str]:
    return sorted(name for name in globals() if not name.startswith('__'))
