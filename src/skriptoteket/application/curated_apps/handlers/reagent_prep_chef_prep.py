from __future__ import annotations

from decimal import Decimal

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemistry,
    ReagentPrepChefLogistics,
    ReagentPrepChefMeta,
    ReagentPrepChefPrepRequest,
    ReagentPrepChefPrepResult,
    ReagentPrepChefPrepSheet,
    ReagentPrepChefSafety,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.reagent_prep_chef import (
    ReagentPrepChefErrorCode,
    build_instructions,
    calculate_numbers,
    collect_warnings,
    rpc_validation_error,
)
from skriptoteket.domain.curated_apps.reagent_prep_chef.formatting import format_decimal
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import PrepInputs
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefHazardStoreProtocol,
    ReagentPrepChefPrepHandlerProtocol,
)


class ReagentPrepChefPrepHandler(ReagentPrepChefPrepHandlerProtocol):
    def __init__(
        self,
        *,
        hazards: ReagentPrepChefHazardStoreProtocol,
        clock: ClockProtocol,
        settings: Settings,
    ) -> None:
        self._hazards = hazards
        self._clock = clock
        self._settings = settings

    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefPrepRequest,
    ) -> ReagentPrepChefPrepResult:
        del actor

        if command.source_type == "liquid_stock":
            if command.stock_molarity is None:
                raise rpc_validation_error(
                    app_code=ReagentPrepChefErrorCode.STOCK_MISSING,
                    message="Ange stockmolaritet när du späder från stocklösning.",
                    details={"field": "stock_molarity"},
                )
            if command.stock_molarity <= command.target_molarity:
                raise rpc_validation_error(
                    app_code=ReagentPrepChefErrorCode.IMPOSSIBLE_DILUTION,
                    message="Målmolariteten måste vara lägre än stockmolariteten.",
                    details={
                        "field": "stock_molarity",
                        "target_molarity": str(command.target_molarity),
                        "stock_molarity": str(command.stock_molarity),
                    },
                )

        inputs = PrepInputs(
            chemical_formula=command.chemical_formula,
            target_molarity=command.target_molarity,
            vol_per_group_ml=command.vol_per_group_ml,
            student_count=command.student_count,
            students_per_group=command.students_per_group,
            safety_factor=command.safety_factor,
            source_type=command.source_type,
            stock_molarity=command.stock_molarity,
            solute_purity=command.solute_purity,
        )

        try:
            numbers = calculate_numbers(request=inputs)
        except Exception as exc:  # noqa: BLE001
            raise rpc_validation_error(
                app_code=ReagentPrepChefErrorCode.INVALID_FORMULA,
                message="Vi kunde inte tolka formeln. Kontrollera stavning och hydratnotation.",
                details={"formula": command.chemical_formula},
            ) from exc

        warnings = collect_warnings(numbers=numbers, min_mass_g=Decimal("0.01"))
        instructions = build_instructions(numbers=numbers)

        hazard_entry = self._hazards.lookup(formula_clean=numbers.formula_clean)
        if hazard_entry is None:
            safety = ReagentPrepChefSafety(
                level="unknown",
                message="Okänt ämne: konsultera SDS innan användning.",
            )
        else:
            safety = ReagentPrepChefSafety(
                level="curated",
                display_name=hazard_entry.display_name,
                hazard_codes=list(hazard_entry.hazard_codes),
                ppe=list(hazard_entry.ppe),
                disposal=hazard_entry.disposal,
                notes=list(hazard_entry.notes),
            )

        total_groups = numbers.total_groups
        base_total_volume_ml = command.vol_per_group_ml * Decimal(total_groups)

        sheet = ReagentPrepChefPrepSheet(
            meta=ReagentPrepChefMeta(
                generated_at=self._clock.now(),
                app_version=self._settings.APP_VERSION,
            ),
            logistics=ReagentPrepChefLogistics(
                total_groups=total_groups,
                base_total_volume_ml=format_decimal(base_total_volume_ml, places=1),
                total_volume_ml=format_decimal(numbers.total_volume_ml, places=1),
                safety_factor_pct=format_decimal(command.safety_factor * Decimal("100"), places=0),
            ),
            chemistry=ReagentPrepChefChemistry(
                source_type=command.source_type,
                formula_clean=numbers.formula_clean,
                molar_mass_g_mol=format_decimal(numbers.molar_mass_g_mol, places=3),
                moles_required=format_decimal(numbers.moles_required, places=4),
                target_molarity=format_decimal(command.target_molarity, places=4),
                solute_purity=format_decimal(command.solute_purity, places=4),
                stock_molarity=(
                    None
                    if command.stock_molarity is None
                    else format_decimal(command.stock_molarity, places=4)
                ),
                mass_g=(
                    None if numbers.mass_g is None else format_decimal(numbers.mass_g, places=2)
                ),
                stock_volume_ml=(
                    None
                    if numbers.stock_volume_ml is None
                    else format_decimal(numbers.stock_volume_ml, places=1)
                ),
                diluent_volume_ml=(
                    None
                    if numbers.diluent_volume_ml is None
                    else format_decimal(numbers.diluent_volume_ml, places=1)
                ),
            ),
            instructions=list(instructions),
            warnings=list(warnings),
            safety=safety,
        )

        return ReagentPrepChefPrepResult(sheet=sheet)
