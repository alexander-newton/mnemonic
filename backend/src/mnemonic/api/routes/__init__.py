"""Mount API routers."""

from fastapi import APIRouter

from mnemonic.api.routes.cards import router as cards_router
from mnemonic.api.routes.config import router as config_router
from mnemonic.api.routes.decks import router as decks_router
from mnemonic.api.routes.reviews import router as reviews_router
from mnemonic.api.routes.usage import router as usage_router
from mnemonic.api.routes.vault import router as vault_router

api_router = APIRouter(prefix="/api")
api_router.include_router(decks_router)
api_router.include_router(cards_router)
api_router.include_router(usage_router)
api_router.include_router(vault_router)
api_router.include_router(config_router)
api_router.include_router(reviews_router)
