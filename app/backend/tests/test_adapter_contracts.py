import unittest

from app.services.adapter_contracts import AdapterContract, validate_adapter_contract
from app.services.provider_capabilities import capabilities_for_route


class AdapterContractTests(unittest.TestCase):
    def test_contract_requires_supported_version_capabilities_and_timeout(self):
        valid = AdapterContract(
            adapter_id="source.test",
            kind="source",
            contract_version="1.0",
            capabilities=("context.read",),
            permissions=("database_read",),
            timeout_seconds=3.0,
            lifecycle="request",
        )
        self.assertIs(valid, validate_adapter_contract(valid, expected_kind="source"))
        with self.assertRaises(ValueError):
            validate_adapter_contract(
                AdapterContract(
                    adapter_id="source.bad",
                    kind="source",
                    contract_version="2.0",
                    capabilities=("context.read",),
                    permissions=(),
                    timeout_seconds=3.0,
                    lifecycle="request",
                ),
                expected_kind="source",
            )

    def test_subscription_provider_declares_session_and_network_permissions(self):
        capabilities = capabilities_for_route(
            {
                "id": "gemini_cli",
                "provider": "google-login",
                "model_id": "gemini-3.1-pro-preview",
                "lazy_start": True,
            }
        )

        self.assertEqual("1.0", capabilities.contract.contract_version)
        self.assertIn("network", capabilities.contract.permissions)
        self.assertIn("account_session", capabilities.contract.permissions)
        self.assertIn("subprocess", capabilities.contract.permissions)
        self.assertEqual("process", capabilities.contract.lifecycle)


if __name__ == "__main__":
    unittest.main()
