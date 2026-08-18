"""Binary Ninja plugin for more agressive DSE (dead_store_elimination)."""

from __future__ import annotations

from typing import List, Optional, Tuple

# Linux: ~/.binaryninja/plugins/aggressive_dse/__init__.py
# macOS: ~/Library/Application Support/Binary Ninja/plugins/aggressive_dse

from binaryninja import (
    PluginCommand,
    log_info,
    log_warn,
    log_error,
)
from binaryninja.enums import DeadStoreElimination


ALLOW_DSE = DeadStoreElimination.AllowDeadStoreElimination
MAX_PASSES = 10


def get_written_variables(func):
    """Return unique Variables written by HLIL instructions in `func`.
    Handles both Variable and SSAVariable objects.
    """

    variables = {}

    try:
        hlil = func.hlil
        if hlil is None:
            return []

        for block in hlil:
            for insn in block:
                for value in getattr(insn, "vars_written", []):
                    var = getattr(value, "var", value)

                    # Variable objects are associated with the owning
                    # function and have a stable storage identifier.
                    try:
                        key = (
                            var.source_type,
                            var.index,
                            var.storage,
                        )
                    except Exception:
                        key = id(var)

                    variables[key] = var

    except Exception as exc:
        log_warn(f"Aggressive DSE: could not inspect {func.name}: {exc}")

    return list(variables.values())


def enable_dse_pass(func):
    """Perform one DSE-enabling pass.

    Returns the number of variables whose setting changed.
    """

    changed = 0

    for var in get_written_variables(func):
        try:
            if var.dead_store_elimination != ALLOW_DSE:
                var.dead_store_elimination = ALLOW_DSE
                changed += 1

        except Exception as exc:
            log_warn(f"Aggressive DSE: failed on variable {var} in {func.name}: {exc}")

    return changed


def aggressive_dse_function(bv, func):
    """Iteratively enable DSE for all variables in one function."""

    log_info(f"Aggressive DSE: processing {func.name} @ {func.start:#x}")

    total = 0

    for pass_number in range(1, MAX_PASSES + 1):
        changed = enable_dse_pass(func)

        if changed == 0:
            break

        total += changed

        log_info(
            f"Aggressive DSE: {func.name}: "
            f"pass {pass_number}, changed {changed} variables"
        )

        func.reanalyze()
        bv.update_analysis_and_wait()

    else:
        log_warn(f"Aggressive DSE: {func.name} reached MAX_PASSES={MAX_PASSES}")

    log_info(f"Aggressive DSE: {func.name}: done, changed {total} variable settings")


def aggressive_dse_binary(bv):
    """Enable DSE across every analyzed function."""
    functions = list(bv.functions)

    log_info(f"Aggressive DSE: processing entire binary ({len(functions)} functions)")

    functions_changed = 0
    variables_changed = 0

    for index, func in enumerate(functions, 1):
        function_total = 0

        try:
            for pass_number in range(1, MAX_PASSES + 1):
                changed = enable_dse_pass(func)

                if changed == 0:
                    break

                function_total += changed

                func.reanalyze()
                bv.update_analysis_and_wait()

            if function_total:
                functions_changed += 1
                variables_changed += function_total

                log_info(
                    f"Aggressive DSE: [{index}/{len(functions)}] "
                    f"{func.name}: {function_total} changes"
                )

        except Exception as exc:
            log_error(f"Aggressive DSE: failed processing {func.name}: {exc}")

    # One final analysis pass after everything has been updated.
    bv.update_analysis_and_wait()

    log_info(
        "Aggressive DSE: binary complete: "
        f"{functions_changed} functions, "
        f"{variables_changed} variable settings changed"
    )


# Plugin registration
PluginCommand.register_for_function(
    r"Aggressive DSE\Current Function",
    "Enable dead-store elimination for variables in the current function",
    aggressive_dse_function,
)

PluginCommand.register(
    r"Aggressive DSE\Entire Binary",
    "Enable dead-store elimination across the entire binary",
    aggressive_dse_binary,
)
