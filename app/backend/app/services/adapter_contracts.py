"""Small, versioned contracts for built-in source/provider/export adapters.

This is intentionally a static internal boundary, not a plugin loader. New
adapters must be imported and registered in source control so capabilities and
permissions remain reviewable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

AdapterKind = Literal["source", "provider", "export"]
AdapterLifecycle = Literal["request", "session", "process"]
AdapterPermission = Literal[
    "database_read",
    "database_write",
    "filesystem_read",
    "filesystem_write",
    "network",
    "account_session",
    "subprocess",
]


@dataclass(frozen=True, slots=True)
class AdapterContract:
    adapter_id: str
    kind: AdapterKind
    contract_version: str
    capabilities: tuple[str, ...]
    permissions: tuple[AdapterPermission, ...]
    timeout_seconds: float
    lifecycle: AdapterLifecycle

    def payload(self) -> dict[str, Any]:
        value = asdict(self)
        value["capabilities"] = list(self.capabilities)
        value["permissions"] = list(self.permissions)
        return value


def validate_adapter_contract(
    contract: AdapterContract,
    *,
    expected_kind: AdapterKind,
) -> AdapterContract:
    if contract.kind != expected_kind:
        raise ValueError(
            f"Adapter {contract.adapter_id} has kind {contract.kind}, expected {expected_kind}"
        )
    major, separator, minor = contract.contract_version.partition(".")
    if not separator or not major.isdigit() or not minor.isdigit():
        raise ValueError(
            f"Adapter {contract.adapter_id} has an invalid contract version"
        )
    if int(major) != 1:
        raise ValueError(
            f"Adapter {contract.adapter_id} uses unsupported contract major {major}"
        )
    if not contract.capabilities:
        raise ValueError(f"Adapter {contract.adapter_id} declares no capabilities")
    if contract.timeout_seconds <= 0:
        raise ValueError(
            f"Adapter {contract.adapter_id} must declare a positive timeout"
        )
    return contract
