"""Application settings and versioned tax assumptions."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from tax_engine import TAX_YEAR as TAX_PARAMETERS


class TaxBracket(BaseModel):
    """Upper taxable-income bound and marginal rate; None means no upper bound."""

    upper_bound: float | None
    rate: float


class TaxYearConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    tax_year: int = TAX_PARAMETERS.tax_year
    standard_deduction_single: float = TAX_PARAMETERS.standard_deduction_single
    traditional_401k_limit: float = TAX_PARAMETERS.traditional_401k_limit
    ira_limit: float = TAX_PARAMETERS.ira_limit
    ira_catch_up_age: int = TAX_PARAMETERS.ira_catch_up_age
    ira_catch_up_limit: float = TAX_PARAMETERS.ira_catch_up_limit
    roth_phaseout_start_single: float = TAX_PARAMETERS.roth_phaseout_start_single
    roth_phaseout_end_single: float = TAX_PARAMETERS.roth_phaseout_end_single
    social_security_wage_base: float = TAX_PARAMETERS.social_security_wage_base
    state_tax_rate_baseline: float = TAX_PARAMETERS.state_tax_rate_baseline
    social_security_rate: float = TAX_PARAMETERS.social_security_rate
    medicare_rate: float = TAX_PARAMETERS.medicare_rate
    additional_medicare_rate: float = TAX_PARAMETERS.additional_medicare_rate
    additional_medicare_threshold_single: float = TAX_PARAMETERS.additional_medicare_threshold_single
    federal_brackets_single: tuple[TaxBracket, ...] = tuple(
        TaxBracket(upper_bound=upper, rate=rate) for upper, rate in TAX_PARAMETERS.federal_brackets_single
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    api_base_url: str = "http://127.0.0.1:8000"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    scenario_db_path: Path = Path("scenario_runs.sqlite3")
    market_data_store: Path = Path("data_cache/published")
    market_history_store: Path = Path("data_cache/local_market_history")
    market_data_mode: Literal["withheld","local_research"] = "withheld"
    app_mode: Literal["ephemeral", "local"] = "ephemeral"
    enable_ai: bool = False

    @property
    def saved_runs_enabled(self) -> bool:
        return self.app_mode == "local"

    @property
    def ai_enabled(self) -> bool:
        return self.app_mode == "local" and self.enable_ai and bool(self.openai_api_key)

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


TAX_YEAR = TaxYearConfig()
