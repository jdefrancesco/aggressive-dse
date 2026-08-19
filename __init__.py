"""Binary Ninja plugin entry point."""

from __future__ import annotations

from .aggressive_dse import run_for_binary, run_for_function


# PluginCommand.register_for_function(
#     r"Aggressive DSE\Current Function",
#     "Enable dead-store elimination for variables in the current function",
#     run_for_function,
# )
#
# PluginCommand.register(
#     r"Aggressive DSE\Entire Binary",
#     "Enable dead-store elimination across the entire binary",
#     run_for_binary,
# )
__all__ = (
    "run_for_binary",
    "run_for_function",
)
