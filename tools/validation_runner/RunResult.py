#
# This file is part of QBDI.
#
# Copyright 2017 - 2023 Quarkslab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import subprocess
from operator import itemgetter
from TestResult import scan_for_pattern, coverage_to_log

class RunResult:
    def __init__(self, test_results=None):
        if test_results is None:
            return
        # Init run info
        self.get_branch_commit()
        self.test_results = test_results
        self.coverage = {}
        self.memaccess_unique = {}
        self.total_instr       = 0
        self.errors            = 0
        self.no_impact_err     = 0
        self.non_critical_err  = 0
        self.critical_err      = 0
        self.cascades          = 0
        self.no_impact_casc    = 0
        self.non_critical_casc = 0
        self.critical_casc     = 0
        self.passed_tests      = 0
        self.memaccess_error   = 0
        # Compute aggregated statistics
        for t in test_results:
            # Only count successfull tests
            if t.retcode == 0 and t.same_output == 1:
                self.total_instr       += t.total_instr
                self.errors            += t.errors
                self.no_impact_err     += t.no_impact_err
                self.non_critical_err  += t.non_critical_err
                self.critical_err      += t.critical_err
                self.cascades          += t.cascades
                self.no_impact_casc    += t.no_impact_casc
                self.non_critical_casc += t.non_critical_casc
                self.critical_casc     += t.critical_casc
                self.memaccess_error   += t.memaccess_error
                self.passed_tests   += 1
                # Aggregate coverage
                for instr, count in t.coverage.items():
                    self.coverage[instr] = self.coverage.get(instr, 0) + count
                for instr, count in t.memaccess_unique.items():
                    self.memaccess_unique[instr] = self.memaccess_unique.get(instr, 0) + count
        self.total_tests = len(test_results)
        self.unique_instr = len(self.coverage)
        self.coverage_log = coverage_to_log(self.coverage.items())
        self.memaccess_unique_log = coverage_to_log(self.memaccess_unique.items())

    @classmethod
    def from_dict(cls, d):
        self = RunResult()
        self.branch = d['branch']
        self.commit = d['commit']
        self.total_instr = d['total_instr']
        self.unique_instr = d['unique_instr']
        self.total_tests = d['total_tests']
        self.passed_tests = d['passed_tests']
        self.errors = d['errors']
        self.no_impact_err = d['no_impact_err']
        self.non_critical_err = d['non_critical_err']
        self.critical_err = d['critical_err']
        self.cascades = d['cascades']
        self.no_impact_casc = d['no_impact_casc']
        self.non_critical_casc = d['non_critical_casc']
        self.critical_casc = d['critical_casc']
        self.memaccess_error = d['memaccess_error']
        self.coverage_log = d['coverage_log']
        self.memaccess_unique_log = d['memaccess_unique_log']
        #Rebuild coverage
        self.coverage = {}
        self.memaccess_unique = {}
        for line in self.coverage_log.split('\n'):
            if ':' in line:
                inst, count = line.split(':')
                self.coverage[inst] = int(count)
        for line in self.memaccess_unique_log.split('\n'):
            if ':' in line:
                inst, count = line.split(':')
                self.memaccess_unique[inst] = int(count)
        self.test_results = []
        return self

    def print_stats(self):
        print(f'[+] Validation result for {self.branch}:{self.commit}')
        print(f'[+] Passed {self.passed_tests}/{self.total_tests} validation tests')
        print(f'[+] Executed {self.total_instr} total instructions')
        print(f'[+] Executed {self.unique_instr} unique instructions')
        print(f'[+] Encountered {self.memaccess_error} memoryAccess errors')
        print(
            f'[+] Encountered {len(list(self.memaccess_unique.items()))} unique memoryAccess errors'
        )
        print(f'[+] Encountered {self.errors} total errors:')
        print(f'[+]     No impact errors: {self.no_impact_err}')
        print(f'[+]     Non critical errors: {self.non_critical_err}')
        print(f'[+]     Critical errors: {self.critical_err}')
        print(f'[+] Encountered {self.cascades} total error cascades:')
        print(f'[+]     No impact cascades: {self.no_impact_casc}')
        print(f'[+]     Non critical cascades: {self.non_critical_casc}')
        print(f'[+]     Critical cascades: {self.critical_casc}')

    def compartive_analysis(self, db):
        prev_run = db.get_last_run(self.branch)
        if prev_run is None:
            prev_run = db.get_last_run('master')
        if prev_run is None:
            print('[+] No previous run in the DB to compare with')
            return
        print(
            f'[+] Comparing with validation run from {prev_run.branch}:{prev_run.commit}'
        )
        regression = 0
        for t1 in prev_run.test_results:
            for t2 in self.test_results:
                # Check if the command and arguments are identical
                if t1.cfg.command == t2.cfg.command and t1.cfg.arguments == t2.cfg.arguments:
                    if t1.retcode == 0 and t2.retcode != 0:
                        print(f'[+] ERROR: Regresssion on test {t1.cfg.command_line()}')
                        # Warn of binary hash change
                        if t1.binary_hash != t2.binary_hash:
                            print('[+] \tWARNING: Binary hashes are not the same')
                        regression += 1
                    elif t2.errors > t1.errors:
                        print(f'[+] WARNING: Increased error count on test {t1.cfg.command_line()}')
                        if t2.no_impact_err > t1.no_impact_err:
                            print(
                                f'[+] \tNo impact errors increased: {t1.no_impact_err} -> {t2.no_impact_err}'
                            )
                        if t2.non_critical_err > t1.non_critical_err:
                            print(
                                f'[+] \tNon critical errors increased: {t1.non_critical_err} -> {t2.non_critical_err}'
                            )
                        # Warn of binary hash change
                        if t1.binary_hash != t2.binary_hash:
                            print('[+] \tWARNING: Binary hashes are not the same')

        if regression == 0:
            print('[+] No regression')
        else:
            print(f'[+] ERROR: {regression} regressions encountered')
        return regression


    def get_branch_commit(self):
        try:
            out = subprocess.check_output(['git', 'status', '-b', '-uno', '--porcelain=2'], universal_newlines=True)
        except Exception as e:
            print(f'[!] git command error : {e}')
            self.commit = 'UNKNOWN'
            self.branch = 'UNKNOWN'
        else:
            self.commit = scan_for_pattern(out, '# branch.oid ([0-9a-fA-F]+)')[0]
            self.branch = scan_for_pattern(out, '# branch.head (\S+)')[0]

    def write_to_db(self, db):
        run_id = db.insert_run_result(self)
        for t in self.test_results:
            db.insert_test_result(run_id, t)
