#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test case for the CodeChecker fixit command's direct functionality.
"""


import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time
import unittest

from shutil import which

from libtest import env


class TestFixit(unittest.TestCase):
    _ccClient = None

    def setup_class(self):
        """Setup the environment for the tests."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('fixit')

        report_dir = os.path.join(TEST_WORKSPACE, 'reports')
        os.makedirs(report_dir)

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    def teardown_class(self):
        """Delete the workspace associated with this test"""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE)

    def setup_method(self, _):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self.report_dir = os.path.join(self.test_workspace, "reports")
        # Change working dir to testfile dir so CodeChecker can be run easily.
        self.__old_pwd = os.getcwd()

    def teardown_method(self, _):
        """Restore environment after tests have run."""
        os.chdir(self.__old_pwd)
        if os.path.isdir(self.report_dir):
            shutil.rmtree(self.report_dir)

    @unittest.skipIf(which('clang-apply-replacements') is None,
                     "clang-apply-replacements clang tool must be available "
                     "in the environment.")
    def test_fixit_list(self):
        '''
        Test that the fixits are generated by clang-tidy
        '''
        # GIVEN
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        source_file_cpp = os.path.join(self.test_workspace, "main.cpp")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "g++ -c -std=c++98 " + source_file_cpp,
                      "file": source_file_cpp
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Test file contents
        simple_file_content = """
#include <vector>
int main()
{
  std::vector<int> v;
  if (v.size() == 0)
    v.push_back(42);
}
"""

        # Write content to the test file
        with open(source_file_cpp, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(simple_file_content)

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clang-tidy", "-o", self.report_dir,
                       "--enable-all"]

        # WHEN
        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        # THEN
        errcode = process.returncode
        self.assertEqual(errcode, 0)

        fixit_dir = os.path.join(self.report_dir, 'fixit')
        self.assertTrue(os.path.isdir(fixit_dir))
        yaml_files = os.listdir(fixit_dir)
        self.assertEqual(len(yaml_files), 1)

        with open(os.path.join(fixit_dir, yaml_files[0]), encoding='utf-8') \
                as f:
            content = f.read()
            self.assertIn("v.empty()", content)

        fixit_list_cmd = [self._codechecker_cmd, "fixit", self.report_dir]

        process = subprocess.Popen(
            fixit_list_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate(input='[]')

        self.assertIn("v.empty()", out)

        fixit_apply_cmd = [self._codechecker_cmd, "fixit", "-a",
                           self.report_dir]

        process = subprocess.Popen(
            fixit_apply_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        process.communicate(input='[]')

        with open(source_file_cpp, encoding="utf-8", errors="ignore") as f:
            new_source_file = f.read()
            self.assertIn("v.empty()", new_source_file)
            self.assertNotIn("v.size()", new_source_file)

    @unittest.skipIf(which('clang-apply-replacements') is None,
                     "clang-apply-replacements clang tool must be available "
                     "in the environment.")
    def test_fixit_file_modification(self):
        # GIVEN
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        source_file_cpp = os.path.join(self.test_workspace, "main.cpp")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "g++ -c -std=c++98 " + source_file_cpp,
                      "file": source_file_cpp
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Test file contents
        simple_file_content = """
#include <vector>
int main()
{
  std::vector<int> v;
  if (v.size() == 0)
    v.push_back(42);
}
"""

        # Write content to the test file
        with open(source_file_cpp, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(simple_file_content)

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clang-tidy", "-o", self.report_dir,
                       "--enable-all"]

        # WHEN
        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        # THEN
        errcode = process.returncode
        self.assertEqual(errcode, 0)

        fixit_dir = os.path.join(self.report_dir, 'fixit')
        self.assertTrue(os.path.isdir(fixit_dir))

        process = subprocess.Popen(
            [self._codechecker_cmd, 'fixit', self.report_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        _, err = process.communicate(input='[]')

        self.assertNotIn(
            'Skipped files due to modification since last analysis',
            err)

        # We're setting the timestamp if the file one hour forward so we
        # simulate file modification. In this case the fixits are not applied
        # and this is also printed to the standard output.
        date = datetime.datetime.now() + datetime.timedelta(hours=1)
        mod_time = time.mktime(date.timetuple())
        os.utime(source_file_cpp, (mod_time, mod_time))

        process = subprocess.Popen(
            [self._codechecker_cmd, 'fixit', self.report_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        _, err = process.communicate(input='[]')

        self.assertIn('Skipped files due to modification since last analysis',
                      err)

    @unittest.skipIf(which('clang-apply-replacements') is None,
                     "clang-apply-replacements clang tool must be available "
                     "in the environment.")
    def test_fixit_by_diff(self):
        # --- Common files and variables --- #

        build_json = os.path.join(self.test_workspace, "build.json")
        source_file = os.path.join(self.test_workspace, "main.c")
        report_dir1 = os.path.join(self.test_workspace, "reports1")
        report_dir2 = os.path.join(self.test_workspace, "reports2")
        source1 = '#include <stdio.h>\n' + \
                  'int main() { printf("%d", "hello"); }'
        source2 = '#include <stdio.h>\n' + \
                  'int main() { printf("%d", "hello");\n' + \
                  'printf("%d", "world"); }'

        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file}]

        with open(build_json, 'w', encoding="utf-8", errors="ignore") as f:
            json.dump(build_log, f)

        # --- Analyze version 1 --- #

        with open(source_file, 'w', encoding="utf-8", errors="ignore") as f:
            f.write(source1)

        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clang-tidy", "-o", "reports1"]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        # --- Analyze version 2 --- #

        with open(source_file, 'w', encoding="utf-8", errors="ignore") as f:
            f.write(source2)

        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clang-tidy", "-o", "reports2"]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        # --- Test fixit --- #

        fixit_cmd = [self._codechecker_cmd, "fixit", report_dir2]

        process = subprocess.Popen(
            fixit_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate(input='[]')
        print(out, err)

        self.assertEqual(out.count('DiagnosticMessage'), 2)

        diff_cmd = [self._codechecker_cmd, "cmd", "diff", "--resolved",
                    "-b", report_dir1, "-n", report_dir2, "-o", "json"]

        process = subprocess.Popen(
            diff_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()
        print('\n' + out + '\n')

        process = subprocess.Popen(
            fixit_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate(input=out)
        print('\n' + out + '\n')
        self.assertEqual(out.count("DiagnosticMessage"), 1)

    @unittest.skipIf(which('clang-apply-replacements') is None,
                     "clang-apply-replacements clang tool must be available "
                     "in the environment.")
    def test_fixit_apply_failure(self):
        def content_hash(filename):
            md5 = hashlib.md5()

            with open(filename, 'rb') as f:
                md5.update(f.read())

            return md5.hexdigest()

        # --- Common files and variables --- #

        build_json = os.path.join(self.test_workspace, "build.json")
        source_file1 = os.path.join(self.test_workspace, "main1.c")
        source_file2 = os.path.join(self.test_workspace, "main2.c")
        report_dir = os.path.join(self.test_workspace, "reports")
        source = '#include <stdio.h>\n' + \
                 'int main() { printf("%d", "hello");\n'

        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file1,
                      "file": source_file1},
                     {"directory": self.test_workspace,
                      "command": "gcc -c " + source_file2,
                      "file": source_file2}]

        with open(build_json, 'w', encoding="utf-8", errors="ignore") as f:
            json.dump(build_log, f)

        # --- Analysis --- #

        with open(source_file1, 'w', encoding="utf-8", errors="ignore") as f:
            f.write(source)
        with open(source_file2, 'w', encoding="utf-8", errors="ignore") as f:
            f.write(source)

        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clang-tidy", "-o", report_dir]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        # --- Test fixit --- #

        orig_hash_1 = content_hash(source_file1)
        orig_hash_2 = content_hash(source_file2)

        # Touch file so "CodeChecker fixit" doesn't apply on the first file.
        # We want to test that the other file is changed despite the failure of
        # this first fail.
        os.utime(source_file1, None)

        fixit_cmd = [self._codechecker_cmd, "fixit", report_dir, "--apply"]

        process = subprocess.Popen(
            fixit_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate(input='[]')

        new_hash_1 = content_hash(source_file1)
        new_hash_2 = content_hash(source_file2)

        # The first file doesn't change due to the touch operation above.
        self.assertEqual(orig_hash_1, new_hash_1)
        self.assertNotEqual(orig_hash_2, new_hash_2)
