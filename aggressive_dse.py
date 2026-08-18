"""Aggressive dead-store elimination commands for Binary Ninja."""

from __future__ import annotations

from typing import TYPE_CHECKING

from binaryninja import BackgroundTaskThread, log_error, log_info, log_warn
from binaryninja.enums import DeadStoreElimination

if TYPE_CHECKING:
    from binaryninja import BinaryView, Function, Variable

ALLOW_DSE = DeadStoreElimination.AllowDeadStoreElimination
MAX_PASSES = 10


def get_written_variables(func: Function) -> list[Variable]:
    """Return the unique non-SSA variables written by a function's HLIL."""
    variables = {}
    hlil = func.hlil
    if hlil is None:
        return []

    for block in hlil:
        for instruction in block:
            for value in instruction.vars_written:
                variable = getattr(value, "var", value)
                key = (variable.source_type, variable.index, variable.storage)
                variables[key] = variable

    return list(variables.values())


def enable_dse_pass(func: Function) -> int:
    """Enable DSE for written variables and return the number changed."""
    changed = 0
    try:
        variables = get_written_variables(func)
    except Exception as exc:
        log_warn(f"Aggressive DSE: could not inspect {func.name}: {exc}")
        return 0

    for variable in variables:
        try:
            if variable.dead_store_elimination != ALLOW_DSE:
                variable.dead_store_elimination = ALLOW_DSE
                changed += 1
        except Exception as exc:
            log_warn(
                f"Aggressive DSE: failed on variable {variable} "
                f"in {func.name}: {exc}"
            )
    return changed


def process_function(bv: BinaryView, func: Function) -> int:
    """Run DSE-enabling passes for one function and return changes made."""
    total = 0
    for pass_number in range(1, MAX_PASSES + 1):
        changed = enable_dse_pass(func)
        if changed == 0:
            break
        total += changed
        log_info(
            f"Aggressive DSE: {func.name}: pass {pass_number}, "
            f"changed {changed} variables"
        )
        func.reanalyze()
        bv.update_analysis_and_wait()
    else:
        log_warn(f"Aggressive DSE: {func.name} reached MAX_PASSES={MAX_PASSES}")
    return total


class AggressiveDSETask(BackgroundTaskThread):
    """Run the potentially expensive analysis without blocking the UI."""

    def __init__(self, bv: BinaryView, func: Function | None = None):
        scope = func.name if func is not None else "entire binary"
        super().__init__(f"Aggressive DSE: {scope}", True)
        self.bv = bv
        self.func = func

    def run(self) -> None:
        if self.func is not None:
            log_info(
                f"Aggressive DSE: processing {self.func.name} "
                f"@ {self.func.start:#x}"
            )
            total = process_function(self.bv, self.func)
            log_info(
                f"Aggressive DSE: {self.func.name}: done, "
                f"changed {total} variable settings"
            )
            return

        functions = list(self.bv.functions)
        functions_changed = 0
        variables_changed = 0
        log_info(
            f"Aggressive DSE: processing entire binary ({len(functions)} functions)"
        )
        for index, func in enumerate(functions, 1):
            if self.cancelled:
                log_warn("Aggressive DSE: cancelled")
                return
            self.progress = f"Aggressive DSE: {index}/{len(functions)} {func.name}"
            try:
                changed = process_function(self.bv, func)
                if changed:
                    functions_changed += 1
                    variables_changed += changed
            except Exception as exc:
                log_error(f"Aggressive DSE: failed processing {func.name}: {exc}")

        self.bv.update_analysis_and_wait()
        log_info(
            "Aggressive DSE: binary complete: "
            f"{functions_changed} functions, "
            f"{variables_changed} variable settings changed"
        )


def run_for_function(bv: BinaryView, func: Function) -> None:
    """Start aggressive DSE for the selected function."""
    AggressiveDSETask(bv, func).start()


def run_for_binary(bv: BinaryView) -> None:
    """Start aggressive DSE for all analyzed functions."""
    AggressiveDSETask(bv).start()
