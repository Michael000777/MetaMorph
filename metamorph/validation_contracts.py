from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


JSONScalar = str | int | float | bool | None

RECOVERABLE_CATEGORIES = {
    "empty_output",
    "invalid_matrix",
    "row_major_orientation",
    "row_length_mismatch",
    "output_name_mismatch",
    "invalid_scalar",
    "invalid_confidence",
}


@dataclass(frozen=True)
class ContractIssue:
    category: str
    message: str
    failed_rows: list[int] = field(default_factory=list)
    recoverable: bool = True


@dataclass(frozen=True)
class ContractValidationResult:
    passed: bool
    issues: list[ContractIssue] = field(default_factory=list)

    @property
    def failed_rows(self) -> list[int]:
        rows: set[int] = set()
        for issue in self.issues:
            rows.update(issue.failed_rows)
        return sorted(rows)

    @property
    def recoverable(self) -> bool:
        return all(issue.recoverable for issue in self.issues)

    @property
    def message(self) -> str:
        return "; ".join(f"{issue.category}: {issue.message}" for issue in self.issues)


def is_json_scalar(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _dedupe_rows(rows: Iterable[int]) -> list[int]:
    return sorted({row for row in rows if row >= 0})


def validate_transformation_contract(
    *,
    raw_values: Sequence[Any],
    transformed_values: Any,
    output_names: Sequence[str] | None = None,
    confidence: Any = None,
) -> ContractValidationResult:
    issues: list[ContractIssue] = []
    expected_rows = len(raw_values)

    if confidence is not None:
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(confidence):
            issues.append(
                ContractIssue(
                    category="invalid_confidence",
                    message=f"Confidence must be a finite number in [0, 1], got {confidence!r}.",
                )
            )
        elif not 0.0 <= float(confidence) <= 1.0:
            issues.append(
                ContractIssue(
                    category="invalid_confidence",
                    message=f"Confidence must be in [0, 1], got {confidence!r}.",
                )
            )

    if not isinstance(transformed_values, list):
        return ContractValidationResult(
            passed=False,
            issues=[
                *issues,
                ContractIssue(
                    category="invalid_matrix",
                    message="Transformed values must be a list of output columns.",
                ),
            ],
        )

    if len(transformed_values) == 0:
        return ContractValidationResult(
            passed=False,
            issues=[
                *issues,
                ContractIssue(
                    category="empty_output",
                    message="Transformed values must include at least one output column.",
                    failed_rows=list(range(expected_rows)),
                ),
            ],
        )

    expected_output_cols = len(output_names) if output_names is not None else None
    if (
        expected_rows > 1
        and expected_output_cols
        and len(transformed_values) == expected_rows
        and expected_output_cols != expected_rows
        and all(isinstance(row, list) and len(row) == expected_output_cols for row in transformed_values)
    ):
        issues.append(
            ContractIssue(
                category="row_major_orientation",
                message=(
                    "Transformed values look row-major; expected columns-first "
                    f"shape with {expected_output_cols} output column(s), not {expected_rows} row(s)."
                ),
                failed_rows=list(range(expected_rows)),
            )
        )

    if output_names is not None and len(output_names) != len(transformed_values):
        issues.append(
            ContractIssue(
                category="output_name_mismatch",
                message=(
                    f"Output name count ({len(output_names)}) must match transformed column count "
                    f"({len(transformed_values)})."
                ),
            )
        )

    for col_idx, column_values in enumerate(transformed_values):
        if not isinstance(column_values, list):
            issues.append(
                ContractIssue(
                    category="invalid_matrix",
                    message=f"Output column {col_idx} must be a list, got {type(column_values).__name__}.",
                )
            )
            continue

        if len(column_values) != expected_rows:
            failed_rows = range(min(len(column_values), expected_rows), max(len(column_values), expected_rows))
            issues.append(
                ContractIssue(
                    category="row_length_mismatch",
                    message=(
                        f"Output column {col_idx} has {len(column_values)} row(s); "
                        f"expected {expected_rows}."
                    ),
                    failed_rows=_dedupe_rows(failed_rows),
                )
            )

        invalid_rows = [
            row_idx
            for row_idx, value in enumerate(column_values[:expected_rows])
            if not is_json_scalar(value)
        ]
        if invalid_rows:
            issues.append(
                ContractIssue(
                    category="invalid_scalar",
                    message=(
                        f"Output column {col_idx} contains non-JSON-scalar values "
                        f"at row(s): {invalid_rows}."
                    ),
                    failed_rows=invalid_rows,
                )
            )

    return ContractValidationResult(
        passed=len(issues) == 0,
        issues=issues,
    )
