from pydantic import BaseModel, Field, ConfigDict


class CombatStats(BaseModel):
    timestamp: list[int] = Field([], description="Дата события или матча")
    damage: list[float] = Field([], description="Нанесённый урон")
    wins: list[float] = Field([], description="Количество побед")
    survival: list[float] = Field([], description="Выживаемость, от 0 до 1")
    battles: list[int] = Field([], description="Количество боёв")
    accuracy: list[float] = Field([], description="Точность стрельбы")

    model_config = ConfigDict(
        from_attributes=True, json_schema_serialization_defaults_required=True
    )
