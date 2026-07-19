"""AGENT: CLI profiling/bootstrap helpers extracted from ``main.py``.

This module is intentionally stdlib-only and side-effect free on import.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Any


def pipela_profile_agent_cli_or_env_enabled(argv: list[str] | None = None, env: Any = None) -> bool:
    argv = sys.argv if argv is None else argv
    env = os.environ if env is None else env
    val = str(env.get("PIPELA_PROFILE_AGENT", "")).strip().lower()
    if val in ("1", "true", "yes"):
        return True
    return "--profile-agent" in argv


def pipela_strip_profile_agent_argv(argv: list[str] | None = None) -> None:
    argv = sys.argv if argv is None else argv
    while "--profile-agent" in argv:
        argv.remove("--profile-agent")


def pipela_copy_standard_readme_agent_dir(agent_dir: str, repo: str) -> None:
    """Skip overwriting ``README.txt`` when ``.pipela_bundle`` marker is present."""
    if os.path.isfile(os.path.join(agent_dir, ".pipela_bundle")):
        return
    tpl = os.path.join(repo, "tools", "profiling_agent_profile_README.txt")
    if os.path.isfile(tpl):
        try:
            shutil.copyfile(tpl, os.path.join(agent_dir, "README.txt"))
        except OSError:
            pass


def pipela_repo_root(main_file: str) -> str:
    return os.path.dirname(os.path.abspath(main_file))


def pipela_write_agent_cprofile_handoff(prof, *, main_file: str, executable: str | None = None) -> None:
    # AGENT: best-effort; mirrors tools/profile_pipela.ps1 + dump_cprofile_summary
    executable = sys.executable if executable is None else executable
    repo = pipela_repo_root(main_file)
    prof_dir = os.path.join(repo, "profiling")
    agent_dir = os.path.join(prof_dir, "agent_profile")
    pending = os.path.join(prof_dir, "_pipela_main_cprofile_pending.stats")
    os.makedirs(prof_dir, exist_ok=True)
    try:
        prof.dump_stats(pending)
    except Exception:
        err = os.path.join(prof_dir, "pipela_cprofile_last_dump_error.txt")
        try:
            with open(err, "w", encoding="utf-8", errors="replace") as ef:
                import traceback as _tb

                ef.write("_pipela_main cProfile.dump_stats failed:\n")
                ef.write(_tb.format_exc())
        except Exception:
            pass
        return
    if not os.path.isfile(pending) or os.path.getsize(pending) < 1:
        return
    os.makedirs(agent_dir, exist_ok=True)
    dest_stats = os.path.join(agent_dir, "cprofile.stats")
    shutil.copyfile(pending, dest_stats)
    try:
        os.remove(pending)
    except OSError:
        pass
    pipela_copy_standard_readme_agent_dir(agent_dir, repo)
    dump_py = os.path.join(repo, "tools", "dump_cprofile_summary.py")
    if os.path.isfile(dump_py):
        r = subprocess.run(
            [executable, dump_py, dest_stats],
            cwd=repo,
            timeout=180,
            check=False,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            err_txt = os.path.join(agent_dir, "cprofile_dump_subproc_error.txt")
            try:
                with open(err_txt, "w", encoding="utf-8", errors="replace") as ef:
                    ef.write(f"returncode={r.returncode}\nstdout=\n{r.stdout}\nstderr=\n{r.stderr}")
            except Exception:
                pass


def pipela_argv_for_profile_child(argv: list[str] | None = None) -> list[str]:
    """Strip meta profiling flags; forwarded to child ``python main.py …``."""
    argv = sys.argv if argv is None else argv
    skip = {
        "--profile-pyspy",
        "--profile-scalene",
        "--profile-agent",
        "--profile-tracemalloc",
    }
    out: list[str] = []
    for a in argv[1:]:
        if a in skip:
            continue
        out.append(a)
    return out


def pipela_subprocess_pyspy_or_exit(
    *,
    argv: list[str] | None = None,
    main_file: str,
    executable: str | None = None,
) -> None:
    """``--profile-pyspy`` → py-spy record child; this process exits."""
    argv = sys.argv if argv is None else argv
    executable = sys.executable if executable is None else executable
    if "--profile-pyspy" not in argv:
        return
    while "--profile-pyspy" in argv:
        argv.remove("--profile-pyspy")
    pyspy = shutil.which("py-spy")
    if not pyspy:
        print("Pipela: py-spy not on PATH (pip install py-spy)", file=sys.stderr, flush=True)
        raise SystemExit(2)
    repo = pipela_repo_root(main_file)
    agent_dir = os.path.join(repo, "profiling", "agent_profile")
    os.makedirs(agent_dir, exist_ok=True)
    pipela_copy_standard_readme_agent_dir(agent_dir, repo)
    out_json = os.path.join(agent_dir, "pyspy.speedscope.json")
    main_py = os.path.join(repo, "main.py")
    rest = pipela_argv_for_profile_child(argv)
    cmd = [
        pyspy,
        "record",
        "-o",
        out_json,
        "--format",
        "speedscope",
        "--rate",
        "100",
        "--subprocesses",
        "--",
        executable,
        main_py,
    ] + rest
    print(f"Pipela: py-spy → {out_json}", flush=True)
    r = subprocess.run(cmd, cwd=repo)
    raise SystemExit(r.returncode)


def pipela_subprocess_scalene_or_exit(
    *,
    argv: list[str] | None = None,
    main_file: str,
) -> None:
    """``--profile-scalene`` → scalene JSON child; this process exits."""
    argv = sys.argv if argv is None else argv
    if "--profile-scalene" not in argv:
        return
    while "--profile-scalene" in argv:
        argv.remove("--profile-scalene")
    scl = shutil.which("scalene")
    if not scl:
        print("Pipela: scalene not on PATH (pip install scalene)", file=sys.stderr, flush=True)
        raise SystemExit(2)
    repo = pipela_repo_root(main_file)
    agent_dir = os.path.join(repo, "profiling", "agent_profile")
    os.makedirs(agent_dir, exist_ok=True)
    out_js = os.path.join(agent_dir, "scalene.json")
    pipela_copy_standard_readme_agent_dir(agent_dir, repo)
    main_py = os.path.join(repo, "main.py")
    rest = pipela_argv_for_profile_child(argv)
    # Scalene >= "run" subcommand: `scalene run -o out.py script.py --- forwarded-args`
    cmd = [scl, "run", "-o", out_js, main_py]
    if rest:
        cmd.extend(["---"] + rest)
    print(f"Pipela: scalene JSON → {out_js}", flush=True)
    r = subprocess.run(cmd, cwd=repo)
    raise SystemExit(r.returncode)


def pipela_tracemalloc_enabled(argv: list[str] | None = None, env: Any = None) -> bool:
    argv = sys.argv if argv is None else argv
    env = os.environ if env is None else env
    val = str(env.get("PIPELA_TRACEMALLOC", "")).strip().lower()
    if val in ("1", "true", "yes"):
        return True
    return "--profile-tracemalloc" in argv


def pipela_tracemalloc_start_maybe(
    *,
    argv: list[str] | None = None,
    env: Any = None,
) -> bool:
    argv = sys.argv if argv is None else argv
    if not pipela_tracemalloc_enabled(argv, env):
        return False
    while "--profile-tracemalloc" in argv:
        argv.remove("--profile-tracemalloc")
    import tracemalloc

    tracemalloc.start(25)
    print("Pipela: tracemalloc on -> profiling/agent_profile/tracemalloc_top.txt on exit", flush=True)
    return True


def pipela_tracemalloc_dump_maybe(was_on: bool, *, main_file: str) -> None:
    if not was_on:
        return
    try:
        import tracemalloc
    except Exception:
        return
    repo = pipela_repo_root(main_file)
    agent_dir = os.path.join(repo, "profiling", "agent_profile")
    try:
        os.makedirs(agent_dir, exist_ok=True)
        path = os.path.join(agent_dir, "tracemalloc_top.txt")
        snap = tracemalloc.take_snapshot()
        lines = [
            "# tracemalloc top 40 lineno (set PIPELA_TRACEMALLOC=1 or --profile-tracemalloc)",
            f"# current_peak_bytes={tracemalloc.get_traced_memory()}",
        ]
        for s in snap.statistics("lineno")[:40]:
            lines.append(str(s))
        with open(path, "w", encoding="utf-8", errors="replace") as fh:
            fh.write("\n".join(lines) + "\n")
    except Exception:
        pass
