import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(
    "/Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "competition_brain_copy_linter", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli(*args, input_text=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


class LintCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.linter = load_module()

    def test_flags_ai_and_official_cliches(self):
        copy = "在当今数字化浪潮下，平台全方位赋能师生，引领教育新范式。"
        findings = self.linter.lint_text(copy)

        expected_categories = {
            ("ai-cliche", "在当今"),
            ("ai-cliche", "全方位"),
            ("ai-cliche", "赋能"),
            ("official-cliche", "引领"),
            ("official-cliche", "新范式"),
        }
        expected_terms = {term for _, term in expected_categories}
        actual_categories = {
            (item["category"], item["term"])
            for item in findings
            if item["term"] in expected_terms
        }
        self.assertEqual(expected_categories, actual_categories)

        for item in findings:
            if item["term"] in expected_terms:
                self.assertEqual(copy.index(item["term"]), item["index"])

        finding_keys = [
            (item["index"], item["category"], item["term"]) for item in findings
        ]
        self.assertEqual(sorted(finding_keys), finding_keys)

    def test_flags_unverifiable_absolutes(self):
        findings = self.linter.lint_text("这是行业领先、全国第一的备赛平台。")
        absolute_findings = {
            (item["category"], item["term"]) for item in findings
        }
        self.assertIn(("unsupported-absolute", "行业领先"), absolute_findings)
        self.assertIn(("unsupported-absolute", "全国第一"), absolute_findings)

    def test_clean_copy_passes(self):
        findings = self.linter.lint_text(
            "路演结束后，问题回到具体页面和视频时点。学生知道下一轮改什么。"
        )
        self.assertEqual([], findings)

    def test_cli_clean_stdin_exits_zero(self):
        result = run_cli(input_text="把每一次反馈变成下一轮行动。")

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_cli_json_findings_from_stdin_exit_one(self):
        result = run_cli("--json", input_text="全方位赋能，引领新范式。")

        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertEqual(
            ["全方位", "赋能", "引领", "新范式"],
            [item["term"] for item in json.loads(result.stdout)],
        )

    def test_cli_reads_utf8_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            copy_path = pathlib.Path(temp_dir) / "中文文案.md"
            copy_path.write_text("这是行业领先的备赛平台。", encoding="utf-8")

            result = run_cli("--json", str(copy_path))

        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertEqual("行业领先", json.loads(result.stdout)[0]["term"])

    def test_cli_reports_each_repeated_term_occurrence(self):
        result = run_cli("--json", input_text="赋能学生，再赋能教师。")

        self.assertEqual(1, result.returncode)
        findings = json.loads(result.stdout)
        self.assertEqual([0, 6], [item["index"] for item in findings])
        self.assertEqual(["赋能", "赋能"], [item["term"] for item in findings])

    def test_cli_missing_file_exits_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = pathlib.Path(temp_dir) / "missing.md"
            result = run_cli(str(missing_path))

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertTrue(result.stderr.startswith("error: "))
        self.assertEqual(1, len(result.stderr.rstrip("\n").splitlines()))
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_non_utf8_file_exits_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = pathlib.Path(temp_dir) / "invalid.txt"
            invalid_path.write_bytes(b"\xff\xfe\x80")
            result = run_cli(str(invalid_path))

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertTrue(result.stderr.startswith("error: "))
        self.assertEqual(1, len(result.stderr.rstrip("\n").splitlines()))
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
