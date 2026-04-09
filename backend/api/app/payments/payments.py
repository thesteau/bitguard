import secrets

from fastapi import FastAPI
from starlette.datastructures import Headers
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network
from x402.server import x402ResourceServer

from app.environments import environments as envs


def _has_internal_access(headers: Headers) -> bool:
    expected_key = envs.INTERNAL_API_KEY.strip()
    provided_key = headers.get("x-internal-api-key", "").strip()
    return bool(
        expected_key
        and provided_key
        and secrets.compare_digest(provided_key, expected_key)
    )


class ConditionalPaymentMiddleware:
    def __init__(self, app, *, routes, server):
        self.app = app
        self.payment_middleware = PaymentMiddlewareASGI(app, routes=routes, server=server)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        if _has_internal_access(headers):
            await self.app(scope, receive, send)
            return

        await self.payment_middleware(scope, receive, send)


def configure_x402(app: FastAPI) -> None:
    if not envs.X402_ENABLED:
        return

    pay_to_address = envs.X402_PAY_TO_ADDRESS.strip()
    if not pay_to_address:
        return

    network: Network = envs.X402_NETWORK

    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(
            url=envs.X402_FACILITATOR_URL
        )
    )

    server = x402ResourceServer(facilitator)
    server.register(network, ExactEvmServerScheme())

    routes: dict[str, RouteConfig] = {
        envs.X402_PROTECTED_ROUTE: RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=pay_to_address,
                    price=envs.X402_PRICE,
                    network=network,
                ),
            ],
            mime_type="application/json",
            description=envs.X402_DESCRIPTION,
        ),
    }

    app.add_middleware(ConditionalPaymentMiddleware, routes=routes, server=server)
