import importlib.util
from pathlib import Path
import sys
import types
import unittest


class FakeBackgroundTaskThread:
    def __init__(self, text, can_cancel):
        self.cancelled = False
        self.progress = text

    def start(self):
        self.run()


binaryninja = types.ModuleType("binaryninja")
binaryninja.BackgroundTaskThread = FakeBackgroundTaskThread
binaryninja.log_error = lambda message: None
binaryninja.log_info = lambda message: None
binaryninja.log_warn = lambda message: None
enums = types.ModuleType("binaryninja.enums")


class DeadStoreElimination:
    AllowDeadStoreElimination = 2


enums.DeadStoreElimination = DeadStoreElimination
sys.modules.setdefault("binaryninja", binaryninja)
sys.modules.setdefault("binaryninja.enums", enums)

module_path = Path(__file__).parents[1] / "aggressive_dse.py"
spec = importlib.util.spec_from_file_location("aggressive_dse_impl", module_path)
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


class FakeVariable:
    def __init__(self, index, setting=0):
        self.source_type = 1
        self.index = index
        self.storage = index * 4
        self.dead_store_elimination = setting


class FakeInstruction:
    def __init__(self, variables):
        self.vars_written = variables


class FakeFunction:
    name = "test"
    start = 0x1000

    def __init__(self, variables):
        self.hlil = [[FakeInstruction(variables)]]
        self.reanalysis_count = 0

    def reanalyze(self):
        self.reanalysis_count += 1


class FakeView:
    def __init__(self, functions=()):
        self.functions = list(functions)
        self.analysis_count = 0

    def update_analysis_and_wait(self):
        self.analysis_count += 1


class AggressiveDSETests(unittest.TestCase):
    def test_written_variables_are_deduplicated(self):
        variable = FakeVariable(1)
        function = FakeFunction([variable, variable])
        self.assertEqual(plugin.get_written_variables(function), [variable])

    def test_process_function_changes_setting_and_reanalyzes(self):
        variable = FakeVariable(1)
        function = FakeFunction([variable])
        view = FakeView([function])
        self.assertEqual(plugin.process_function(view, function), 1)
        self.assertEqual(variable.dead_store_elimination, plugin.ALLOW_DSE)
        self.assertEqual(function.reanalysis_count, 1)
        self.assertEqual(view.analysis_count, 1)

    def test_missing_hlil_is_a_noop(self):
        function = FakeFunction([])
        function.hlil = None
        self.assertEqual(plugin.get_written_variables(function), [])


if __name__ == "__main__":
    unittest.main()
