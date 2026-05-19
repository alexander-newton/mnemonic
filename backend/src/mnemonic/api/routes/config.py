"""Config UI endpoint (read-only in Phase 1)."""

from fastapi import APIRouter, Depends

from mnemonic.api.deps import get_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_current_config(cfg=Depends(get_config)):
    return {
        "vault": {"path": str(cfg.vault.path), "branch": cfg.vault.branch, "watch": cfg.vault.watch},
        "llm": {
            "model_default": cfg.llm.model_default,
            "model_rephrase": cfg.llm.model_rephrase,
            "model_offline": cfg.llm.model_offline,
            "budget": {
                "daily_cents": cfg.llm.budget.daily_cents,
                "monthly_cents": cfg.llm.budget.monthly_cents,
            },
        },
        "defaults": cfg.defaults.__dict__,
    }
