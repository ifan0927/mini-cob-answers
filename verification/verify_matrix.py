#!/usr/bin/env python3
"""Re-runs the exercise verification matrix for mini-cob.

  (a) baseline           -> every test passes
  (b) learner            -> every exercise test fails, for the reason listed in expected-failures.tsv,
                            both in the full suite and when run alone; every non-exercise test passes
  (c) learner + fix i    -> exercise i passes; every other exercise still fails; non-exercise tests pass

The learner tree is rebuilt as baseline + patches/bugs/*.patch. When --learner points at a delivered
learner repo, its sources are compared with the rebuilt tree first, so the check covers what was shipped.
"Fix i" means reverse-applying patches/bugs/i.patch to the learner tree.

Usage:
  python3 verify_matrix.py [--learner ../../mini-cob-learner] [--only 03,07] [--repeat 1] [--report out.md]
Requires: Java 21, git, network access to Maven Central for the first build.
"""
import argparse
import datetime
import filecmp
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.dirname(HERE)
BASELINE = os.path.join(ANSWERS, "baseline")
BUG_PATCHES = os.path.join(ANSWERS, "patches", "bugs")
EXPECTED = os.path.join(HERE, "expected-failures.tsv")
IGNORED = {"target", ".git", ".idea"}


def load_expectations():
    rows = {}
    with open(EXPECTED, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            number, cls, regex = line.rstrip("\n").split("\t")
            rows[number] = (cls, re.compile(regex))
    return rows


def copy_tree(src, dst):
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if n in IGNORED])


def git_apply(tree, patch, reverse=False):
    cmd = ["git", "apply", "--whitespace=nowarn"] + (["-R"] if reverse else []) + [patch]
    subprocess.run(cmd, cwd=tree, check=True)


def run_suite(tree, label, log_dir):
    """Runs the whole suite; returns {simple class name: (passed, message)}."""
    reports = os.path.join(tree, "target", "surefire-reports")
    shutil.rmtree(reports, ignore_errors=True)
    log_path = os.path.join(log_dir, label + ".log")
    started = time.time()
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.run(["./mvnw", "-B", "-q", "test", "-Dsurefire.printSummary=true"],
                              cwd=tree, stdout=log, stderr=subprocess.STDOUT)
    elapsed = time.time() - started
    results = {}
    if os.path.isdir(reports):
        for name in sorted(os.listdir(reports)):
            if not (name.startswith("TEST-") and name.endswith(".xml")):
                continue
            suite = ET.parse(os.path.join(reports, name)).getroot()
            cls = suite.get("name").rsplit(".", 1)[-1]
            failures = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
            tests = int(suite.get("tests", 0))
            messages = []
            for case in suite.iter("testcase"):
                for kind in ("failure", "error"):
                    for node in case.iter(kind):
                        messages.append((node.get("message") or "") + "\n" + (node.text or ""))
            results[cls] = (tests > 0 and failures == 0, "\n".join(messages))
    if not results:
        raise RuntimeError(f"{label}: no test reports (exit code {proc.returncode}); see {log_path}")
    return results, elapsed


def run_single(tree, cls, label, log_dir):
    """Runs one test class the way task.md tells the learner to; returns (passed, message)."""
    reports = os.path.join(tree, "target", "surefire-reports")
    shutil.rmtree(reports, ignore_errors=True)
    with open(os.path.join(log_dir, label + ".log"), "w", encoding="utf-8") as log:
        subprocess.run(["./mvnw", "-B", "-q", "test", f"-Dtest={cls}"], cwd=tree, stdout=log, stderr=subprocess.STDOUT)
    xml = os.path.join(reports, f"TEST-com.minicob.exercises.{cls}.xml")
    if not os.path.exists(xml):
        return False, "no report (compilation error?)"
    suite = ET.parse(xml).getroot()
    failed = int(suite.get("failures", 0)) + int(suite.get("errors", 0)) > 0
    messages = [(n.get("message") or "") + "\n" + (n.text or "") for kind in ("failure", "error") for n in suite.iter(kind)]
    return not failed, "\n".join(messages)


def short(message, limit=160):
    first = " ".join(line.strip() for line in message.strip().splitlines()[:4] if line.strip())
    return (first[:limit] + "...") if len(first) > limit else first


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--learner", help="delivered learner repo to compare against baseline + bug patches")
    parser.add_argument("--only", help="comma-separated exercise numbers for step (c), e.g. 03,07")
    parser.add_argument("--repeat", type=int, default=1, help="repeat steps (b) and (c) N times to catch flakiness")
    parser.add_argument("--report", default=os.path.join(HERE, "matrix-result.md"))
    parser.add_argument("--keep", action="store_true", help="keep the work directory")
    parser.add_argument("--no-single", action="store_true", help="skip running each exercise test on its own in step (b)")
    args = parser.parse_args()

    expectations = load_expectations()
    exercises = sorted(expectations)
    selected = args.only.split(",") if args.only else exercises
    exercise_classes = {cls for cls, _ in expectations.values()}
    work = tempfile.mkdtemp(prefix="mini-cob-matrix-")
    logs = os.path.join(work, "logs")
    os.makedirs(logs)
    lines, problems = [], []

    def record(ok, text):
        lines.append(("PASS  " if ok else "FAIL  ") + text)
        print(lines[-1], flush=True)
        if not ok:
            problems.append(text)

    # Build the learner tree.
    learner = os.path.join(work, "learner")
    copy_tree(BASELINE, learner)
    for number in exercises:
        git_apply(learner, os.path.join(BUG_PATCHES, number + ".patch"))
    if args.learner:
        diff = filecmp.dircmp(os.path.join(learner, "src"), os.path.join(args.learner, "src"))
        mismatches = []

        def walk(d, prefix=""):
            mismatches.extend(prefix + n for n in d.left_only + d.right_only + d.diff_files)
            for sub, child in d.subdirs.items():
                walk(child, prefix + sub + "/")
        walk(diff)
        record(not mismatches, f"delivered learner src == baseline + bug patches {mismatches if mismatches else ''}")

    baseline_copy = os.path.join(work, "baseline")
    copy_tree(BASELINE, baseline_copy)

    for round_no in range(1, args.repeat + 1):
        tag = f"[round {round_no}] " if args.repeat > 1 else ""
        # (a) baseline
        results, elapsed = run_suite(baseline_copy, f"a-baseline-{round_no}", logs)
        failing = [c for c, (ok, _) in results.items() if not ok]
        record(not failing, f"{tag}(a) baseline: {len(results)} test classes, all pass ({elapsed:.0f}s) {failing if failing else ''}")
        # (b) learner
        results, elapsed = run_suite(learner, f"b-learner-{round_no}", logs)
        for cls, (ok, _) in sorted(results.items()):
            if cls not in exercise_classes:
                record(ok, f"{tag}(b) learner: non-exercise {cls} passes")
        for number in exercises:
            cls, regex = expectations[number]
            ok, message = results.get(cls, (True, "missing report"))
            matches = (not ok) and bool(regex.search(message))
            record(matches, f"{tag}(b) learner: Ex{number} fails for its own reason -> {short(message)}")
        if not args.no_single:
            for number in exercises:
                cls, regex = expectations[number]
                ok, message = run_single(learner, cls, f"b-single-{number}-{round_no}", logs)
                matches = (not ok) and bool(regex.search(message))
                record(matches, f"{tag}(b) learner, run alone (-Dtest={cls}): fails for its own reason -> {short(message, 110)}")

        # (c) learner with only fix i
        for number in selected:
            tree = os.path.join(work, f"fix-{number}")
            shutil.rmtree(tree, ignore_errors=True)
            copy_tree(learner, tree)
            git_apply(tree, os.path.join(BUG_PATCHES, number + ".patch"), reverse=True)
            results, elapsed = run_suite(tree, f"c-fix-{number}-{round_no}", logs)
            target_cls = expectations[number][0]
            target_ok = results.get(target_cls, (False, "missing"))[0]
            still_failing = [n for n in exercises if n != number and not results.get(expectations[n][0], (True, ""))[0]]
            others_ok = len(still_failing) == len(exercises) - 1
            plain_ok = all(ok for c, (ok, _) in results.items() if c not in exercise_classes)
            record(target_ok, f"{tag}(c) fix only {number}: Ex{number} passes ({elapsed:.0f}s)")
            record(others_ok, f"{tag}(c) fix only {number}: the other {len(exercises) - 1} exercises still fail "
                              f"({len(still_failing)} failing)")
            record(plain_ok, f"{tag}(c) fix only {number}: non-exercise tests pass")
            shutil.rmtree(tree, ignore_errors=True)

    with open(args.report, "w", encoding="utf-8") as out:
        out.write(f"# mini-cob verification matrix\n\nRun at {datetime.datetime.now().isoformat(timespec='seconds')}\n\n")
        out.write("```\n" + "\n".join(lines) + "\n```\n\n")
        out.write(f"Result: {'ALL CHECKS PASSED' if not problems else str(len(problems)) + ' CHECK(S) FAILED'}\n")
        out.write(f"\nLogs: {logs}\n")
    print(f"\nReport written to {args.report}; logs in {logs}")
    if not args.keep and not problems:
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
