"""Esquema compartilhado pelo baseline, LLM, app e avaliação."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Contrato(BaseModel):
    """O Pydantic verifica tipos, datas reais e a presença das oito chaves.

    Cada chave é obrigatória no JSON, mas seu valor pode ser nulo se o
    contrato omitir a informação. A validação estrutural não confere fatos.
    """

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    locador: str | None = Field(min_length=1)
    locatario: str | None = Field(min_length=1)
    endereco_imovel: str | None = Field(min_length=1)
    valor_aluguel: float | None = Field(ge=0)
    prazo_meses: int | None = Field(gt=0)
    data_inicio: date | None
    valor_multa_rescisoria: float | None = Field(ge=0)
    indice_reajuste: str | None = Field(min_length=1)
