from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class TextAIResponse(StrictModel):
    reply: str = Field(min_length=1, max_length=1600)


class PatientAIResponse(StrictModel):
    reply: str = Field(min_length=1, max_length=1800)
    is_treatment: bool
    treatment_assessment: Literal['NOT_APPLICABLE', 'ADEQUATE', 'PARTIAL', 'INADEQUATE']

    @model_validator(mode='after')
    def validate_treatment_consistency(self):
        if self.is_treatment and self.treatment_assessment == 'NOT_APPLICABLE':
            raise ValueError('Tratamento concreto exige uma classificação de adequação.')
        if not self.is_treatment and self.treatment_assessment != 'NOT_APPLICABLE':
            raise ValueError('Sem tratamento concreto, a classificação deve ser NOT_APPLICABLE.')
        return self


class EvaluationDomains(StrictModel):
    comunicacao: int = Field(ge=0, le=10)
    anamnese: int = Field(ge=0, le=20)
    sinais_alarme: int = Field(ge=0, le=15)
    investigacao: int = Field(ge=0, le=15)
    raciocinio: int = Field(ge=0, le=20)
    conduta: int = Field(ge=0, le=15)
    seguimento: int = Field(ge=0, le=5)

    @property
    def total(self) -> int:
        return (
            self.comunicacao
            + self.anamnese
            + self.sinais_alarme
            + self.investigacao
            + self.raciocinio
            + self.conduta
            + self.seguimento
        )


class EvaluationAIResponse(StrictModel):
    score: int = Field(ge=0, le=100)
    case_summary: str = Field(min_length=1, max_length=2400)
    care_summary: str = Field(min_length=1, max_length=3000)
    strengths: list[str] = Field(default_factory=list, max_length=5)
    reinforcement: list[str] = Field(default_factory=list, max_length=5)
    study_topics: list[str] = Field(default_factory=list, max_length=6)
    domains: EvaluationDomains

    @model_validator(mode='after')
    def validate_score_matches_rubric(self):
        if self.score != self.domains.total:
            raise ValueError('A nota geral deve ser a soma dos sete domínios da rubrica.')
        return self
