"""Pydantic models owned by the software-engineering layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ai import Ingredient, Nutrition, NutritionFacts


AnalysisStatus = Literal["ok", "unknown_meal", "partial"]


class IngredientNutrition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient: Ingredient
    facts: NutritionFacts | None = None
    nutrition: Nutrition = Field(default_factory=Nutrition)
    error: str | None = None


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    status: AnalysisStatus
    image_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ingredients: list[Ingredient] = Field(default_factory=list)
    rows: list[IngredientNutrition] = Field(default_factory=list)
    totals: Nutrition = Field(default_factory=Nutrition)
    errors: list[str] = Field(default_factory=list)

    @property
    def meal_recognized(self) -> bool:
        return self.status != "unknown_meal"


class HistoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    image_path: str
    status: AnalysisStatus
    ingredients: list[Ingredient]
    rows: list[IngredientNutrition]
    totals: Nutrition
    errors: list[str] = Field(default_factory=list)

    @classmethod
    def from_result(cls, result: AnalysisResult) -> "HistoryRecord":
        return cls(
            id=result.id,
            created_at=result.created_at,
            image_path=result.image_path,
            status=result.status,
            ingredients=result.ingredients,
            rows=result.rows,
            totals=result.totals,
            errors=result.errors,
        )


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: AnalysisResult
