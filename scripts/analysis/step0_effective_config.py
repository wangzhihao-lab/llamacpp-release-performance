#!/usr/bin/env python3
"""Root-cause protocol, step 0: the effective configuration of every tag.

For each of the 81 selected llama.cpp tags, collect the configuration that was in
effect when the campaign built and benchmarked it, then list every point where that
configuration changes between consecutive tags (sorted by build number).

Sources (all local and read-only; nothing is built, benchmarked or downloaded):

* ``results/<tag>/records.csv`` and ``results/<tag>/<model>_<backend>.json``: what
  llama-bench reports it ran with (n_threads, n_batch, n_ubatch, flash_attn,
  type_k/type_v, use_mmap, poll, repack, backends, ...).
* ``results/<tag>/llama-bench_help.txt``: the defaults the binary declares.
* ``results/<tag>/build_meta.tsv``: compiler, CMake version, CMake arguments, option era.
* ``results/<tag>/cmake_configure.log``: what CMake detected (Accelerate, BLAS, Metal,
  OpenMP, ARM flags, check results).
* ``results/<tag>/cmake_build.log``: first compiler error of build-failed tags.
* ``src/<tag>.tar.gz``: CMake option defaults and the ARM flag logic, evaluated for
  this machine (APPLE, arm64, Apple clang) by a small CMake-subset interpreter fed with
  the check results of the configure log.  Members are read in memory, never extracted.
* ``cc <flags> -dM -E -x c /dev/null`` (preprocessor only) to list the ``__ARM_FEATURE_*``
  macros each distinct CPU flag set actually defines (skip with ``--no-compiler-probe``).
* ``repo/`` (blob-less clone) ``git log`` metadata for the build-info regression, with
  lazy fetching and all transport protocols disabled.

Outputs (``results/analysis/``):

* ``effective_config.csv``: one row per tag (raw + normalised ``eff_*`` columns).
* ``config_changes.csv``: one row per configuration change (machine-readable; step 1 reads it).
* ``config_changes.md``: change table, constant items, build-failure patch suggestions.

Run from the repository root: uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step0_effective_config.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
SRC = ROOT / "src"
REPO = ROOT / "repo"
OUT_DIR = RESULTS / "analysis"
TAGS_FILE = ROOT / "data" / "selected_tags.txt"

BACKENDS = ("metal", "cpu")
MODELS = ("tinyllama-1.1b", "mistral-7b", "qwen2.5-1.5b")
CMAKE_FILES = (
    "CMakeLists.txt",
    "ggml/CMakeLists.txt",
    "ggml/src/CMakeLists.txt",
    "ggml/src/ggml-cpu/CMakeLists.txt",
    "ggml/src/ggml-metal/CMakeLists.txt",
    "ggml/src/ggml-blas/CMakeLists.txt",
)
EXTRA_SOURCE_FILES = ("scripts/build-info.cmake",)
# Options whose effective value is reported; looked up with the LLAMA_ and GGML_ prefix.
OPTIONS = (
    "NATIVE", "ACCELERATE", "BLAS", "LLAMAFILE", "OPENMP", "CPU_AARCH64", "CPU_REPACK",
    "CPU_KLEIDIAI", "METAL", "METAL_EMBED_LIBRARY", "METAL_USE_BF16", "METAL_NDEBUG",
    "METAL_SHADER_DEBUG", "LTO", "BACKEND_DL", "CPU_ALL_VARIANTS",
)
ARM_MACROS = ("DOTPROD", "FMA", "FP16_VECTOR_ARITHMETIC", "MATMUL_INT8", "BF16", "SVE", "SME")
JSON_SKIP = {
    "avg_ns", "stddev_ns", "avg_ts", "stddev_ts", "samples_ns", "samples_ts", "test_time",
    "n_prompt", "n_gen", "n_depth", "model_filename", "model_type", "model_size", "model_n_params",
    "build_commit", "build_number",
}

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- CMake subset


TRUE_CONSTS = {"1", "ON", "YES", "TRUE", "Y"}
FALSE_CONSTS = {"0", "OFF", "NO", "FALSE", "N", "IGNORE", "NOTFOUND", ""}
UNARY_OPS = {"DEFINED", "EXISTS", "COMMAND", "TARGET", "POLICY", "TEST", "IS_DIRECTORY", "IS_ABSOLUTE",
             "IS_SYMLINK"}
BINARY_OPS = {"STREQUAL", "MATCHES", "EQUAL", "LESS", "GREATER", "LESS_EQUAL", "GREATER_EQUAL",
              "VERSION_LESS", "VERSION_GREATER", "VERSION_EQUAL", "VERSION_LESS_EQUAL",
              "VERSION_GREATER_EQUAL", "STRLESS", "STRGREATER", "IN_LIST", "PATH_EQUAL"}
VAR_REF = re.compile(r"\$\{([^${}]*)\}")
ENV_REF = re.compile(r"\$ENV\{[^}]*\}")
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
BRACKET_OPEN = re.compile(r"\[(=*)\[")
FLAG_RE = re.compile(r"^-(march|mcpu|mtune|mfpu|mfp16-format|U__ARM_FEATURE)")


@dataclass(frozen=True)
class Command:
    """One CMake command invocation.

    Attributes:
        name: Lower-case command name.
        args: Arguments as (text, quoted) pairs; nested parentheses are separate tokens.
        line: Line number of the command name.
    """

    name: str
    args: tuple[tuple[str, bool], ...]
    line: int


@dataclass
class CMakeVar:
    """A CMake variable as seen by the interpreter.

    Attributes:
        value: Value (lists joined with ';').
        certain: False when it depends on a branch or input the interpreter cannot decide.
    """

    value: str
    certain: bool


def _parse_args(text: str, i: int, line: int) -> tuple[list[tuple[str, bool]], int, int]:
    """Parse the argument list of a command starting after its '('.

    Args:
        text: Whole file.
        i: Index just after the opening parenthesis.
        line: Current line number.

    Returns:
        (arguments, index after the closing parenthesis, line number there).
    """
    args: list[tuple[str, bool]] = []
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
        elif c in " \t\r":
            i += 1
        elif c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c == "(":
            depth += 1
            args.append(("(", False))
            i += 1
        elif c == ")":
            if depth == 0:
                return args, i + 1, line
            depth -= 1
            args.append((")", False))
            i += 1
        elif c == '"':
            j = i + 1
            buf: list[str] = []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(text[j + 1], text[j + 1]))
                    j += 2
                    continue
                if text[j] == "\n":
                    line += 1
                buf.append(text[j])
                j += 1
            args.append(("".join(buf), True))
            i = j + 1
        elif c == "[" and BRACKET_OPEN.match(text, i):
            m = BRACKET_OPEN.match(text, i)
            assert m is not None
            close = "]" + m.group(1) + "]"
            j = text.find(close, m.end())
            j = n if j < 0 else j
            body = text[m.end():j]
            line += body.count("\n")
            args.append((body, True))
            i = j + len(close)
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()#"':
                j += 2 if text[j] == "\\" else 1
            args.append((text[i:j], False))
            i = j
    return args, i, line


def parse_cmake(text: str) -> list[Command]:
    """Split a CMake file into command invocations.

    Args:
        text: File content.

    Returns:
        Commands in file order.
    """
    cmds: list[Command] = []
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        if c == "#":
            m = BRACKET_OPEN.match(text, i + 1)
            if m:
                close = "]" + m.group(1) + "]"
                j = text.find(close, m.end())
                j = n if j < 0 else j + len(close)
                line += text.count("\n", i, j)
                i = j
            else:
                j = text.find("\n", i)
                i = n if j < 0 else j
            continue
        m = NAME_RE.match(text, i)
        if not m:
            i += 1
            continue
        j = m.end()
        while j < n and text[j] in " \t":
            j += 1
        if j >= n or text[j] != "(":
            i = j
            continue
        start_line = line
        args, i, line = _parse_args(text, j + 1, line)
        cmds.append(Command(m.group(0).lower(), tuple(args), start_line))
    return cmds


def _tri_and(a: bool | None, b: bool | None) -> bool | None:
    """Three-valued AND (None = unknown)."""
    if a is False or b is False:
        return False
    if a is True and b is True:
        return True
    return None


def _tri_or(a: bool | None, b: bool | None) -> bool | None:
    """Three-valued OR (None = unknown)."""
    if a is True or b is True:
        return True
    if a is False and b is False:
        return False
    return None


def _tri_not(a: bool | None) -> bool | None:
    """Three-valued NOT (None = unknown)."""
    return None if a is None else not a


def _const_truth(text: str) -> bool | None:
    """Truth of a CMake constant, or None if ``text`` is not a constant."""
    up = text.strip().upper()
    if up in TRUE_CONSTS:
        return True
    if up in FALSE_CONSTS or up.endswith("-NOTFOUND"):
        return False
    try:
        return float(up) != 0.0
    except ValueError:
        return None


def _value_truth(value: str) -> bool:
    """Truth of a variable's value in ``if(<variable>)``."""
    c = _const_truth(value)
    return True if c is None else c


def _version_tuple(text: str) -> tuple[int, ...]:
    """Parse '1.2.3' into a tuple of ints (non-numeric parts become 0)."""
    return tuple(int(p) if p.isdigit() else 0 for p in re.split(r"[.]", text.strip()) if p != "")


class _Break(Exception):
    """Raised by an active ``break()`` inside ``foreach``."""


class _Return(Exception):
    """Raised by an active ``return()`` at file level."""


@dataclass
class _Frame:
    """State of one ``if`` block."""

    parent: bool | None
    taken: bool | None
    active: bool | None


@dataclass
class CMakeEval:
    """Evaluate the parts of llama.cpp's CMake files that decide options and CPU flags.

    Supported: if/elseif/else/endif with full condition syntax, foreach (ITEMS/LISTS),
    set/unset/option/list(APPEND)/string(APPEND|TOLOWER|TOUPPER|JOIN|REPLACE),
    add_compile_options, add_compile_definitions, check_* (results taken from the
    configure log), find_* (from log facts), break/return.  function/macro bodies are
    skipped (newer ARM flags live in one; the configure log prints them instead).

    Attributes:
        vars: Variable table.
        unknown: Variables assigned by commands that are not modelled.
        options: Option name -> (resolved value, certain) for every option() seen.
        flags: (flag, certain) collected from add_compile_options / ARCH_FLAGS.
        defs: (definition, certain) collected from add_compile_definitions.
    """

    vars: dict[str, CMakeVar] = field(default_factory=dict)
    unknown: set[str] = field(default_factory=set)
    options: dict[str, tuple[str, bool]] = field(default_factory=dict)
    flags: list[tuple[str, bool]] = field(default_factory=list)
    defs: list[tuple[str, bool]] = field(default_factory=list)
    found: dict[str, str] = field(default_factory=dict)
    stack: list[_Frame] = field(default_factory=list)

    # -- variables ---------------------------------------------------------------
    def lookup(self, name: str) -> tuple[str, bool]:
        """Return (value, certain) of a variable; undefined -> ('', True) unless unknown."""
        if name in self.vars:
            v = self.vars[name]
            return v.value, v.certain
        if name.startswith("CACHE{") and name.endswith("}"):
            return self.lookup(name[6:-1])
        return "", name not in self.unknown

    def expand(self, text: str) -> tuple[str, bool]:
        """Expand ``${VAR}`` references (innermost first); ``$ENV{X}`` expands to ''."""
        certain = True
        text = ENV_REF.sub("", text)
        for _ in range(32):
            m = VAR_REF.search(text)
            if not m:
                break
            val, c = self.lookup(m.group(1))
            certain = certain and c
            text = text[:m.start()] + val + text[m.end():]
        return text, certain

    def set_var(self, name: str, value: str, certain: bool) -> None:
        """Assign a variable (uncertain context makes it uncertain)."""
        self.vars[name] = CMakeVar(value, certain)
        self.unknown.discard(name)

    @property
    def active(self) -> bool | None:
        """Whether the current position executes (None = unknown)."""
        return self.stack[-1].active if self.stack else True

    # -- conditions --------------------------------------------------------------
    def _operand(self, tok: tuple[str, bool, bool]) -> tuple[str, bool]:
        """Value of a binary-operator operand: variable value if it names one."""
        text, quoted, certain = tok
        if not quoted and NAME_RE.fullmatch(text) and (text in self.vars or text in self.unknown):
            val, c = self.lookup(text)
            return val, certain and c
        return text, certain

    def _truth(self, tok: tuple[str, bool, bool]) -> bool | None:
        """Truth of a lone operand (constant, quoted string or variable name)."""
        text, quoted, certain = tok
        if not certain:
            return None
        const = _const_truth(text)
        if quoted:
            return bool(const)
        if const is not None:
            return const
        if text in self.vars:
            v = self.vars[text]
            return _value_truth(v.value) if v.certain else None
        if text in self.unknown:
            return None
        return False

    def _binary(self, op: str, left: tuple[str, bool, bool], right: tuple[str, bool, bool]) -> bool | None:
        """Evaluate a binary test."""
        lv, lc = self._operand(left)
        if op == "IN_LIST":
            rv, rc = self.lookup(right[0])
            return (lv in rv.split(";")) if (lc and rc) else None
        rv, rc = self._operand(right)
        if not (lc and rc):
            return None
        try:
            if op == "STREQUAL":
                return lv == rv
            if op == "MATCHES":
                return re.search(rv, lv) is not None
            if op in {"EQUAL", "LESS", "GREATER", "LESS_EQUAL", "GREATER_EQUAL"}:
                a, b = float(lv), float(rv)
                return {"EQUAL": a == b, "LESS": a < b, "GREATER": a > b,
                        "LESS_EQUAL": a <= b, "GREATER_EQUAL": a >= b}[op]
            if op.startswith("VERSION_"):
                a2, b2 = _version_tuple(lv), _version_tuple(rv)
                return {"VERSION_LESS": a2 < b2, "VERSION_GREATER": a2 > b2, "VERSION_EQUAL": a2 == b2,
                        "VERSION_LESS_EQUAL": a2 <= b2, "VERSION_GREATER_EQUAL": a2 >= b2}[op]
            if op == "STRLESS":
                return lv < rv
            if op == "STRGREATER":
                return lv > rv
        except (ValueError, re.error):
            return None
        return None

    def _unary(self, op: str, arg: tuple[str, bool, bool]) -> bool | None:
        """Evaluate a unary test."""
        text = arg[0]
        if op == "DEFINED":
            if text.startswith("ENV{"):
                return False
            name = text[6:-1] if text.startswith("CACHE{") else text
            if name in self.unknown:
                return None
            return name in self.vars
        if op == "EXISTS" and text.rstrip("/").endswith(".git"):
            return False  # builds run on release tarballs without .git
        return None

    def condition(self, args: tuple[tuple[str, bool], ...]) -> bool | None:
        """Evaluate an if()/elseif() condition with CMake precedence."""
        toks: list[tuple[str, bool, bool]] = []
        for text, quoted in args:
            if not quoted and text in ("(", ")"):
                toks.append((text, False, True))
                continue
            val, c = self.expand(text)
            toks.append((val, quoted, c))
        pos = 0

        def peek() -> tuple[str, bool, bool] | None:
            return toks[pos] if pos < len(toks) else None

        def is_kw(word: str) -> bool:
            t = peek()
            return t is not None and not t[1] and t[0] == word

        def p_or() -> bool | None:
            nonlocal pos
            v = p_and()
            while is_kw("OR"):
                pos += 1
                v = _tri_or(v, p_and())
            return v

        def p_and() -> bool | None:
            nonlocal pos
            v = p_not()
            while is_kw("AND"):
                pos += 1
                v = _tri_and(v, p_not())
            return v

        def p_not() -> bool | None:
            nonlocal pos
            if is_kw("NOT"):
                pos += 1
                return _tri_not(p_not())
            return p_primary()

        def p_primary() -> bool | None:
            nonlocal pos
            t = peek()
            if t is None:
                return None
            if not t[1] and t[0] == "(":
                pos += 1
                v = p_or()
                if is_kw(")"):
                    pos += 1
                return v
            if not t[1] and t[0] in UNARY_OPS:
                pos += 1
                arg = peek()
                pos += 1
                return self._unary(t[0], arg) if arg is not None else None
            pos += 1
            nxt = peek()
            if nxt is not None and not nxt[1] and nxt[0] in BINARY_OPS:
                pos += 1
                right = peek()
                pos += 1
                return self._binary(nxt[0], t, right) if right is not None else None
            return self._truth(t)

        return p_or()

    # -- execution ---------------------------------------------------------------
    def _values(self, args: tuple[tuple[str, bool], ...]) -> tuple[list[str], bool]:
        """Expand arguments; unquoted ones are split on ';' like CMake lists."""
        out: list[str] = []
        certain = True
        for text, quoted in args:
            val, c = self.expand(text)
            certain = certain and c
            if quoted:
                out.append(val)
            else:
                out.extend(p for p in val.split(";") if p != "")
        return out, certain

    def run_file(self, text: str, current_dir: str) -> None:
        """Execute one CMake file.

        Args:
            text: File content.
            current_dir: Value for CMAKE_CURRENT_SOURCE_DIR.
        """
        self.set_var("CMAKE_CURRENT_SOURCE_DIR", current_dir, True)
        self.set_var("CMAKE_CURRENT_LIST_DIR", current_dir, True)
        self.stack = []
        try:
            self._run_block(parse_cmake(text))
        except _Return:
            pass
        self.stack = []

    def _run_block(self, cmds: list[Command]) -> None:
        """Execute a list of commands (handles foreach and skips function bodies)."""
        i = 0
        while i < len(cmds):
            cmd = cmds[i]
            if cmd.name in ("function", "macro"):
                i = self._skip_to(cmds, i, cmd.name, "end" + cmd.name)
                continue
            if cmd.name == "foreach":
                end = self._skip_to(cmds, i, "foreach", "endforeach")
                self._run_foreach(cmd, cmds[i + 1:end - 1])
                i = end
                continue
            self._exec(cmd)
            i += 1

    @staticmethod
    def _skip_to(cmds: list[Command], i: int, opener: str, closer: str) -> int:
        """Index just after the command closing the block opened at ``i``."""
        depth = 0
        for j in range(i, len(cmds)):
            if cmds[j].name == opener:
                depth += 1
            elif cmds[j].name == closer:
                depth -= 1
                if depth == 0:
                    return j + 1
        return len(cmds)

    def _run_foreach(self, head: Command, body: list[Command]) -> None:
        """Run a foreach body for each item (ITEMS, LISTS or a plain list)."""
        if self.active is False or not head.args:
            return
        var = head.args[0][0]
        rest = head.args[1:]
        items: list[str] = []
        certain = True
        if rest and not rest[0][1] and rest[0][0] == "IN":
            mode = ""
            for text, quoted in rest[1:]:
                if not quoted and text in ("ITEMS", "LISTS", "ZIP_LISTS"):
                    mode = text
                    continue
                if mode == "LISTS":
                    val, c = self.lookup(text)
                    items.extend(p for p in val.split(";") if p)
                    certain = certain and c
                else:
                    vals, c = self._values(((text, quoted),))
                    items.extend(vals)
                    certain = certain and c
        elif rest and not rest[0][1] and rest[0][0] == "RANGE":
            return
        else:
            items, certain = self._values(rest)
        depth = len(self.stack)
        for item in items:
            self.set_var(var, item, certain)
            try:
                self._run_block(body)
            except _Break:
                del self.stack[depth:]
                break

    def _exec(self, cmd: Command) -> None:
        """Execute one command."""
        name, args = cmd.name, cmd.args
        if name == "if":
            parent = self.active
            cond = self.condition(args) if parent is not False else False
            self.stack.append(_Frame(parent, cond, _tri_and(parent, cond)))
            return
        if name == "elseif":
            if not self.stack:
                return
            fr = self.stack[-1]
            cond = self.condition(args) if fr.parent is not False else False
            fr.active = _tri_and(fr.parent, _tri_and(_tri_not(fr.taken), cond))
            fr.taken = _tri_or(fr.taken, cond)
            return
        if name == "else":
            if self.stack:
                fr = self.stack[-1]
                fr.active = _tri_and(fr.parent, _tri_not(fr.taken))
            return
        if name == "endif":
            if self.stack:
                self.stack.pop()
            return
        act = self.active
        if act is False:
            return
        sure = act is True
        if name == "break":
            if sure:
                raise _Break()
            return
        if name == "return":
            if sure and not self.stack:
                raise _Return()
            return
        if name == "set" and args:
            self._exec_set(args, sure)
        elif name == "unset" and args:
            self.vars.pop(args[0][0], None)
        elif name == "option" and args:
            opt = args[0][0]
            raw = args[2] if len(args) >= 3 else ("OFF", False)
            val, c = self.expand(raw[0])
            if opt not in self.vars:
                self.set_var(opt, val, sure and c)
            self.options[opt] = (self.vars[opt].value, self.vars[opt].certain)
        elif name == "list" and len(args) >= 2 and args[0][0] == "APPEND":
            var = args[1][0]
            vals, c = self._values(args[2:])
            old, oc = self.lookup(var)
            items = [p for p in old.split(";") if p] + vals
            self.set_var(var, ";".join(items), sure and c and oc)
        elif name == "string" and args:
            self._exec_string(args, sure)
        elif name in ("add_compile_options", "add_definitions", "add_compile_definitions"):
            vals, c = self._values(args)
            for v in vals:
                if name == "add_compile_options" and FLAG_RE.match(v):
                    self.flags.append((v, sure and c))
                elif name != "add_compile_options":
                    self.defs.append((v.removeprefix("-D"), sure and c))
        elif name.startswith("check_") and len(args) >= 2:
            var = self.expand(args[-1][0])[0]
            if var in self.found:
                self.set_var(var, self.found[var], True)
            elif var not in self.vars:
                self.unknown.add(var)
        elif name in ("find_library", "find_program", "find_path", "find_file") and args:
            var = args[0][0]
            if var in self.found:
                self.set_var(var, self.found[var], True)
            elif var not in self.vars:
                self.unknown.add(var)
        elif name == "find_package" and args:
            pkg = args[0][0]
            for var in (f"{pkg}_FOUND", f"{pkg.upper()}_FOUND"):
                if var in self.found:
                    self.set_var(var, self.found[var], True)
                elif var not in self.vars:
                    self.unknown.add(var)
        elif name == "execute_process":
            words = [a[0] for a in args]
            for k, w in enumerate(words[:-1]):
                if w in ("OUTPUT_VARIABLE", "RESULT_VARIABLE", "ERROR_VARIABLE"):
                    self.unknown.add(words[k + 1])
                    self.vars.pop(words[k + 1], None)

    def _exec_set(self, args: tuple[tuple[str, bool], ...], sure: bool) -> None:
        """set(VAR values... [CACHE TYPE DOC [FORCE]] [PARENT_SCOPE])."""
        var = self.expand(args[0][0])[0]
        rest = list(args[1:])
        cache = False
        force = False
        words = [a[0] if not a[1] else None for a in rest]
        if "CACHE" in words:
            k = words.index("CACHE")
            force = "FORCE" in words[k:]
            rest = rest[:k]
            cache = True
        rest = [a for a in rest if not (not a[1] and a[0] == "PARENT_SCOPE")]
        if cache and var in self.vars and not force:
            return
        if not rest:
            self.vars.pop(var, None)
            return
        vals, c = self._values(tuple(rest))
        self.set_var(var, ";".join(vals), sure and c)

    def _exec_string(self, args: tuple[tuple[str, bool], ...], sure: bool) -> None:
        """string(APPEND|TOLOWER|TOUPPER|JOIN|REPLACE ...); other forms mark output unknown."""
        sub = args[0][0]
        if sub == "APPEND" and len(args) >= 2:
            old, oc = self.lookup(args[1][0])
            vals, c = self._values(args[2:])
            self.set_var(args[1][0], old + "".join(vals), sure and c and oc)
        elif sub in ("TOLOWER", "TOUPPER") and len(args) >= 3:
            val, c = self.expand(args[1][0])
            self.set_var(args[2][0], val.lower() if sub == "TOLOWER" else val.upper(), sure and c)
        elif sub == "JOIN" and len(args) >= 3:
            glue, gc = self.expand(args[1][0])
            vals, c = self._values(args[3:])
            self.set_var(args[2][0], glue.join(vals), sure and c and gc)
        elif sub == "REPLACE" and len(args) >= 5:
            m, mc = self.expand(args[1][0])
            r, rc = self.expand(args[2][0])
            vals, c = self._values(args[4:])
            self.set_var(args[3][0], "".join(vals).replace(m, r), sure and mc and rc and c)
        elif sub == "REGEX" and len(args) >= 4:
            self.unknown.add(args[3][0])
            self.vars.pop(args[3][0], None)


# --------------------------------------------------------------------------- readers


def read_kv_tsv(path: Path) -> dict[str, str]:
    """Read ``key<TAB>value`` lines (later keys win); missing file -> {}.

    Args:
        path: TSV file.

    Returns:
        Mapping key -> value.
    """
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(errors="replace").splitlines():
        if "\t" in line:
            k, v = line.split("\t", 1)
            out[k] = v.strip()
    return out


def read_text(path: Path) -> str:
    """Return the text of ``path`` or '' if it does not exist."""
    return path.read_text(errors="replace") if path.is_file() else ""


def load_bench_json(path: Path) -> list[dict[str, Any]]:
    """Parse a llama-bench ``-o json`` file, tolerating junk before/after the array.

    Args:
        path: JSON file.

    Returns:
        List of test records ([] if unreadable).
    """
    text = read_text(path)
    start = text.find("[")
    if start < 0:
        return []
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return []
    return [r for r in obj if isinstance(r, dict)] if isinstance(obj, list) else []


HELP_LINE = re.compile(r"^\s*(-{1,2}[A-Za-z][\w-]*)(?:\s+(?:N|<[^>]*>))?(?:\s*,\s*(--[\w-]+))?(.*)$")


def parse_help(text: str) -> dict[str, str]:
    """Extract ``--long-option -> default`` from ``llama-bench --help`` output.

    Args:
        text: Help text.

    Returns:
        Mapping; deprecated options map to 'DEPRECATED', options without a default to ''.
    """
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = HELP_LINE.match(line)
        if not m:
            continue
        key = m.group(2) or m.group(1)
        rest = m.group(3)
        d = re.search(r"\(default:\s*([^)]*)\)", rest)
        if "DEPRECATED" in rest:
            out[key] = "DEPRECATED"
        else:
            out[key] = d.group(1).strip() if d else out.get(key, "")
    return out


def read_source_members(tag: str, rels: tuple[str, ...]) -> dict[str, str]:
    """Read selected files from ``src/<tag>.tar.gz`` without extracting it.

    Args:
        tag: Release tag.
        rels: Paths relative to the source root.

    Returns:
        Mapping rel path -> text for the members found.
    """
    path = SRC / f"{tag}.tar.gz"
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    wanted = set(rels)
    try:
        with tarfile.open(path, "r|gz") as tf:
            for m in tf:
                if not m.isfile() or "/" not in m.name:
                    continue
                rel = m.name.split("/", 1)[1]
                if rel in wanted:
                    fh = tf.extractfile(m)
                    if fh is not None:
                        out[rel] = fh.read().decode("utf-8", "replace")
                    if len(out) == len(wanted):
                        break
    except (tarfile.TarError, OSError, EOFError) as exc:
        logger.warning("%s: cannot read tarball: %s", tag, exc)
    return out


# --------------------------------------------------------------------------- configure log


CHECK_RE = re.compile(r"^-- Performing Test (\S+) - (Success|Failed)")


def configure_facts(log: str) -> dict[str, str]:
    """Turn configure-log lines into variable facts for the interpreter.

    Args:
        log: cmake_configure.log text.

    Returns:
        Variable -> value (check results, find results).
    """
    found: dict[str, str] = {}
    for line in log.splitlines():
        m = CHECK_RE.match(line)
        if m:
            found[m.group(1)] = "1" if m.group(2) == "Success" else ""
    if "Accelerate framework found" in log:
        found["ACCELERATE_FRAMEWORK"] = "/System/Library/Frameworks/Accelerate.framework"
    if "Metal framework found" in log:
        for v in ("METAL_FRAMEWORK", "FOUNDATION_LIBRARY", "METALKIT_FRAMEWORK"):
            found[v] = f"/System/Library/Frameworks/{v}.framework"
    found["BLAS_FOUND"] = "TRUE" if re.search(r"^-- Found BLAS", log, re.MULTILINE) else "FALSE"
    found["OpenMP_FOUND"] = "TRUE" if re.search(r"^-- Found OpenMP", log, re.MULTILINE) else "FALSE"
    found["OPENMP_FOUND"] = found["OpenMP_FOUND"]
    found["Git_FOUND"] = found["GIT_FOUND"] = "TRUE" if "-- Found Git" in log else "FALSE"
    found["Threads_FOUND"] = "TRUE"
    found["OpenSSL_FOUND"] = found["OPENSSL_FOUND"] = "TRUE" if "-- Found OpenSSL" in log else "FALSE"
    return found


def summarize_configure(log: str) -> dict[str, str]:
    """Pick the configure-log lines that describe the build configuration.

    Args:
        log: cmake_configure.log text.

    Returns:
        Flat dict of ``cfg_*`` columns.
    """
    def has(pat: str) -> bool:
        return re.search(pat, log, re.MULTILINE) is not None

    variant = re.findall(r"^-- Adding CPU backend variant ggml-cpu:\s*(.*?)\s*$", log, re.MULTILINE)
    arm_enabled = re.findall(r"^-- ARM feature (\S+) enabled", log, re.MULTILINE)
    have_ok = re.findall(r"^-- Performing Test HAVE_(\S+) - Success", log, re.MULTILINE)
    have_fail = [f for f in re.findall(r"^-- Performing Test HAVE_(\S+) - Failed", log, re.MULTILINE) if f != "SVE"]
    machine = re.findall(r"^-- Performing Test GGML_MACHINE_SUPPORTS_(\S+) - Success", log, re.MULTILINE)
    ggml_ver = re.findall(r"^-- ggml version:\s*(\S+)", log, re.MULTILINE)
    llama_ver = re.findall(r"^-- llama.cpp version:\s*(\S+)", log, re.MULTILINE)
    if has(r"^-- Using llamafile"):
        llamafile_msg = "Using llamafile"
    elif has(r"^-- Using ggml SGEMM"):
        llamafile_msg = "Using ggml SGEMM"
    else:
        llamafile_msg = ""
    if has(r"Could NOT find OpenMP \(missing"):
        openmp = "not found"
    elif has(r"^-- Found OpenMP"):
        openmp = "found"
    else:
        openmp = "not checked"
    return {
        "cfg_accelerate": "found" if "Accelerate framework found" in log else "",
        "cfg_blas": "Accelerate" if has(r"^-- Found BLAS: .*Accelerate") else ("found" if has(r"^-- Found BLAS") else ""),
        "cfg_blas_backend_msg": "yes" if has(r"^-- Including BLAS backend") else "",
        "cfg_metal": "found" if "Metal framework found" in log else "",
        "cfg_metal_backend_msg": "yes" if has(r"^-- Including METAL backend") else "",
        "cfg_openmp": openmp,
        "cfg_llamafile_msg": llamafile_msg,
        "cfg_cpu_variant_flags": variant[0] if variant else "",
        "cfg_arm_features_enabled": ",".join(arm_enabled or have_ok),
        "cfg_arm_feature_probe_failed": ",".join(have_fail),
        "cfg_machine_supports": ",".join(machine),
        "cfg_q4_0_runtime_repack_msg": "yes" if "runtime weight conversion of Q4_0" in log else "",
        "cfg_ggml_version": ggml_ver[0] if ggml_ver else "",
        "cfg_llama_version": llama_ver[0] if llama_ver else "",
        "cfg_openssl": "found" if "-- Found OpenSSL" in log else "",
        "cfg_fp16_format_ieee": ("supported" if has(r"FP16_FORMAT_I3E - Success") else
                                 ("unsupported" if has(r"FP16_FORMAT_I3E - Failed") else "")),
    }


# --------------------------------------------------------------------------- per-tag extraction


MACHINE_FACTS = {
    "APPLE": "1", "UNIX": "1", "CMAKE_SYSTEM_NAME": "Darwin", "CMAKE_HOST_SYSTEM_NAME": "Darwin",
    "CMAKE_SYSTEM_PROCESSOR": "arm64", "CMAKE_HOST_SYSTEM_PROCESSOR": "arm64",
    "CMAKE_C_COMPILER_ID": "AppleClang", "CMAKE_CXX_COMPILER_ID": "AppleClang",
    "CMAKE_C_COMPILER_VERSION": "17.0.0.17000603", "CMAKE_CXX_COMPILER_VERSION": "17.0.0.17000603",
    "CMAKE_C_COMPILER": "/usr/bin/cc", "CMAKE_CXX_COMPILER": "/usr/bin/c++",
    "CMAKE_OSX_ARCHITECTURES": "", "CMAKE_GENERATOR": "Unix Makefiles", "CMAKE_GENERATOR_PLATFORM": "",
    "CMAKE_C_FLAGS": "", "CMAKE_CXX_FLAGS": "", "CMAKE_REQUIRED_FLAGS": "", "CMAKE_CROSSCOMPILING": "FALSE",
    "CMAKE_VERSION": "4.4.0", "CMAKE_SOURCE_DIR": "/src", "PROJECT_SOURCE_DIR": "/src",
    "CMAKE_BINARY_DIR": "/build", "CMAKE_CURRENT_BINARY_DIR": "/build", "CMAKE_SIZEOF_VOID_P": "8",
}


def parse_cmake_args(cmake_args: str) -> dict[str, str]:
    """Extract ``-DNAME=VALUE`` pairs from the recorded CMake command line."""
    return dict(re.findall(r"-D([A-Za-z0-9_]+)=(\S*)", cmake_args))


def evaluate_source(tag: str, files: dict[str, str], cmake_args: str, log: str) -> dict[str, Any]:
    """Run the CMake-subset interpreter on a tag's CMake files.

    Args:
        tag: Release tag (for logging).
        files: rel path -> text of the CMake files.
        cmake_args: Recorded CMake arguments of the campaign build.
        log: Configure log (check results).

    Returns:
        Dict with option values, collected arch flags and definitions.
    """
    ev = CMakeEval()
    for k, v in MACHINE_FACTS.items():
        ev.set_var(k, v, True)
    for k, v in parse_cmake_args(cmake_args).items():
        ev.set_var(k, v, True)
    ev.found = configure_facts(log)
    order = {"CMakeLists.txt": "/src", "ggml/CMakeLists.txt": "/src/ggml", "ggml/src/CMakeLists.txt": "/src/ggml/src",
             "ggml/src/ggml-cpu/CMakeLists.txt": "/src/ggml/src/ggml-cpu",
             "ggml/src/ggml-metal/CMakeLists.txt": "/src/ggml/src/ggml-metal",
             "ggml/src/ggml-blas/CMakeLists.txt": "/src/ggml/src/ggml-blas"}
    for rel, cur in order.items():
        if rel in files:
            ev.run_file(files[rel], cur)
    flags = list(ev.flags)
    for var in ("ARCH_FLAGS",):
        val, c = ev.lookup(var)
        for item in [p for p in re.split(r"[;\s]+", val) if p]:
            if FLAG_RE.match(item):
                flags.append((item, c))
    seen: set[str] = set()
    uniq: list[tuple[str, bool]] = []
    for f, c in flags:
        if f not in seen:
            seen.add(f)
            uniq.append((f, c))
    result: dict[str, Any] = {"flags": uniq, "defs": sorted({d for d, _ in ev.defs})}
    for opt in OPTIONS:
        for prefix in ("GGML_", "LLAMA_"):
            name = prefix + opt
            if name in ev.vars or name in ev.options:
                v = ev.vars.get(name)
                if v is not None:
                    result[opt] = (v.value, v.certain, name)
                    break
    logger.debug("%s: flags=%s options=%s", tag, uniq, {k: result.get(k) for k in OPTIONS})
    return result


def _onoff(item: tuple[str, bool, str] | None) -> str:
    """Format an option value as on/off/n/a, with '?' when uncertain."""
    if item is None:
        return "n/a"
    value, certain, _ = item
    txt = "on" if _value_truth(value) else "off"
    return txt if certain else txt + "?"


def json_values(tag_dir: Path, backend: str, ok_models: list[str]) -> dict[str, str]:
    """Collect JSON config fields of one back end over all models that ran ok.

    Args:
        tag_dir: results/<tag>.
        backend: metal or cpu.
        ok_models: Models with ok records for this back end.

    Returns:
        key -> value (values differing between models are joined with '|').
    """
    vals: dict[str, list[str]] = {}
    for model in ok_models:
        recs = load_bench_json(tag_dir / f"{model}_{backend}.json")
        for rec in recs[:1]:
            for k, v in rec.items():
                if k in JSON_SKIP:
                    continue
                vals.setdefault(k, [])
                s = json.dumps(v) if not isinstance(v, str) else v
                if s not in vals[k]:
                    vals[k].append(s)
    return {k: "|".join(v) for k, v in vals.items()}


def norm_bool(text: str) -> str:
    """Normalise JSON booleans/ints ('true', 'false', '1', '0') to '1'/'0'."""
    t = text.strip().lower()
    if t in ("true", "1"):
        return "1"
    if t in ("false", "0"):
        return "0"
    return text


def runtime_effective(j: dict[str, str]) -> dict[str, str]:
    """Normalise the JSON fields of one back end into comparable ``eff_*`` values.

    Args:
        j: Output of json_values() for one back end.

    Returns:
        Dict of normalised values (semantically equal settings map to the same string).
    """
    out: dict[str, str] = {}
    out["threads"] = j.get("n_threads", "")
    out["ngl"] = j.get("n_gpu_layers", "")
    nb = j.get("n_batch", "")
    out["n_batch"] = nb
    out["n_ubatch"] = j.get("n_ubatch", nb)  # before ubatch existed the whole batch ran at once
    fa = j.get("flash_attn")
    if fa is None:
        out["flash_attn"] = "off"
    else:
        out["flash_attn"] = {"0": "off", "1": "on", "-1": "auto"}.get(norm_bool(fa), fa)
    if "type_k" in j:
        out["kv_type"] = f"{j.get('type_k', '')}/{j.get('type_v', j.get('type_k', ''))}"
    elif "f16_kv" in j:
        out["kv_type"] = "f16/f16" if norm_bool(j["f16_kv"]) == "1" else "f32/f32"
    else:
        out["kv_type"] = ""
    if "load_mode" in j:
        out["model_load"] = j["load_mode"]
    else:
        mm = norm_bool(j.get("use_mmap", "true"))
        dio = norm_bool(j.get("use_direct_io", "false"))
        out["model_load"] = {("1", "0"): "mmap", ("1", "1"): "mmap+dio", ("0", "0"): "read",
                             ("0", "1"): "dio"}.get((mm, dio), f"mmap={mm},dio={dio}")
    out["poll"] = j.get("poll", "n/a (pre-threadpool)")
    out["cpu_mask"] = j.get("cpu_mask", "0x0") + "/" + norm_bool(j.get("cpu_strict", "false"))
    out["no_kv_offload"] = norm_bool(j.get("no_kv_offload", "false"))
    out["split_mode"] = j.get("split_mode", "layer")
    out["embeddings"] = norm_bool(j.get("embeddings", "false"))
    if "backends" in j:
        names = {p.strip().lower() for p in j["backends"].split(",") if p.strip()}
    else:
        names = {k for k in ("metal", "blas", "cuda", "vulkan", "opencl", "sycl", "kompute")
                 if norm_bool(j.get(k, "false")) == "1"}
    out["backends"] = ",".join(sorted({"metal" if n in ("mtl", "metal") else n for n in names}))
    out["repack_json"] = norm_bool(j["repack"]) if "repack" in j else ""
    out["no_op_offload"] = norm_bool(j["no_op_offload"]) if "no_op_offload" in j else ""
    return out


def extract_tag(tag: str, compiler_macros: dict[str, str]) -> dict[str, Any]:
    """Build the effective-configuration row of one tag.

    Args:
        tag: Release tag.
        compiler_macros: Cache flag-set -> macro list (filled lazily).

    Returns:
        Row dict.
    """
    tag_dir = RESULTS / tag
    meta = read_kv_tsv(tag_dir / "build_meta.tsv")
    status = {}
    if (tag_dir / "status.json").is_file():
        try:
            status = json.loads(read_text(tag_dir / "status.json"))
        except json.JSONDecodeError:
            status = {}
    log = read_text(tag_dir / "cmake_configure.log")
    row: dict[str, Any] = {
        "tag": tag,
        "build_number": int(tag[1:]),
        "commit_date_utc": meta.get("commit_date_utc", ""),
        "build_commit": meta.get("tarball_commit") or meta.get("release_commit", ""),
        "status": status.get("status", meta.get("stage", "")),
        "option_era": meta.get("option_era", ""),
        "bench_src_dir": meta.get("bench_src_dir", ""),
        "compiler": meta.get("compiler", ""),
        "cmake": meta.get("cmake", ""),
        "macos": meta.get("macos", ""),
        "host_model": meta.get("host_model", ""),
        "power": meta.get("power", ""),
        "cmake_args": meta.get("cmake_args", ""),
        "binary_bytes": meta.get("binary_bytes", ""),
        "linked_libs_nonsystem": meta.get("linked_libs", "").strip(),
        "cpu_no_op_offload_flag": meta.get("cpu_no_op_offload_flag", ""),
        "configure_s": meta.get("configure_s", ""),
        "build_s": meta.get("build_s", ""),
    }
    row.update(summarize_configure(log))

    # ---- source (CMake defaults, ARM flag logic) ----
    files = read_source_members(tag, CMAKE_FILES + EXTRA_SOURCE_FILES)
    src = evaluate_source(tag, files, row["cmake_args"], log)
    for opt in OPTIONS:
        item = src.get(opt)
        row[f"src_{opt.lower()}"] = _onoff(item)
        row[f"src_{opt.lower()}_name"] = item[2] if item else ""
    row["src_arch_flags"] = " ".join(f + ("" if c else "?") for f, c in src["flags"])
    row["src_defs"] = " ".join(d for d in src["defs"] if re.match(r"(GGML_USE_|__ARM_FEATURE|ACCELERATE_)", d))
    bi = files.get("scripts/build-info.cmake", "")
    row["src_build_info_sha12"] = hashlib.sha256(bi.encode()).hexdigest()[:12] if bi else ""
    row["src_build_info_guarded"] = ("yes" if "RESULT_VARIABLE" in bi else "no") if bi else "n/a"

    # ---- effective CPU flags + compiler-defined ARM macros ----
    if row["cfg_cpu_variant_flags"]:
        # "Adding CPU backend variant ggml-cpu: <ARCH_FLAGS> <ARCH_DEFINITIONS>"
        toks = [f for f in re.split(r"[;\s]+", row["cfg_cpu_variant_flags"]) if f]
        flags = [t for t in toks if t.startswith("-")]
        arm_defs = [t for t in toks if not t.startswith("-") and t.startswith("__ARM_FEATURE")]
        flag_src = "configure log"
    else:
        flags = [f for f, _ in src["flags"]]
        arm_defs = [d for d in src["defs"] if d.startswith("__ARM_FEATURE")]
        flag_src = "source eval" if files else "n/a"
        if any(not c for _, c in src["flags"]):
            flag_src += " (uncertain)"
    # -U__ARM_FEATURE_X only removes a macro; its effect shows up in eff_arm_macros.
    undefs = [f for f in flags if f.startswith("-U")]
    codegen = [f for f in flags if not f.startswith("-U")]
    row["eff_arm_flags"] = " ".join(codegen) if codegen else "none (clang default -mcpu=apple-m1)"
    row["eff_arm_undefs_defs"] = " ".join(undefs + [f"-D{d}" for d in arm_defs])
    row["eff_arm_flags_source"] = flag_src
    probe = flags + [f"-D{d}" for d in arm_defs]
    key = " ".join(probe)
    if key not in compiler_macros:
        compiler_macros[key] = probe_arm_macros(probe)
    row["eff_arm_macros"] = compiler_macros[key]

    # ---- build-level normalised values ----
    blas_on = row["src_blas"].startswith("on") and row["cfg_blas"] != ""
    row["eff_accelerate"] = "on" if (row["src_accelerate"].startswith("on") and row["cfg_accelerate"]) else "off"
    row["eff_blas_backend"] = "on (Accelerate)" if blas_on else "off"
    row["eff_llamafile"] = "on" if row["src_llamafile"].startswith("on") else "off"
    row["eff_openmp"] = "on" if (row["src_openmp"].startswith("on") and row["cfg_openmp"] == "found") else "off"
    repack = row["src_cpu_repack"] if row["src_cpu_repack"] != "n/a" else row["src_cpu_aarch64"]
    row["eff_cpu_repack"] = "on" if repack.startswith("on") else "off"
    row["eff_kleidiai"] = "on" if row["src_cpu_kleidiai"].startswith("on") else "off"
    row["eff_native_option"] = row["src_native"]
    args = parse_cmake_args(row["cmake_args"])
    embed = args.get("GGML_METAL_EMBED_LIBRARY") or args.get("LLAMA_METAL_EMBED_LIBRARY") or ""
    if not row["cmake_args"]:
        row["eff_metal_library"] = ""
    else:
        row["eff_metal_library"] = ("embedded source, runtime compile" if _const_truth(embed)
                                    else "ggml-metal.metal file, runtime compile")
    row["eff_metal_bf16"] = "on" if row["src_metal_use_bf16"].startswith("on") else "off"
    row["eff_metal_shader_debug"] = "on" if row["src_metal_shader_debug"].startswith("on") else "off"

    # ---- runtime (records + JSON + help) ----
    rec_path = tag_dir / "records.csv"
    recs = pd.read_csv(rec_path, dtype=str).fillna("") if rec_path.is_file() else pd.DataFrame()
    help_defaults = parse_help(read_text(tag_dir / "llama-bench_help.txt"))
    row["help_defaults"] = json.dumps(help_defaults, sort_keys=True) if help_defaults else ""
    for opt in ("--threads", "--batch-size", "--ubatch-size", "--flash-attn", "--cache-type-k",
                "--cache-type-v", "--mmap", "--direct-io", "--load-mode", "--poll", "--n-gpu-layers",
                "--no-op-offload", "--repack", "--prio", "--delay"):
        row["help_" + opt.lstrip("-").replace("-", "_")] = help_defaults.get(opt, "")
    ok_models_all: set[str] = set()
    for backend in BACKENDS:
        ok = []
        if not recs.empty:
            sub = recs[(recs.backend == backend) & (recs.status == "ok")]
            ok = [m for m in MODELS if m in set(sub.model)]
            ok_models_all.update(ok)
            ea = sorted(set(recs[recs.backend == backend].extra_args))
            row[f"{backend}_extra_args"] = "|".join(ea)
        j = json_values(tag_dir, backend, ok)
        row[f"{backend}_json"] = json.dumps(j, sort_keys=True) if j else ""
        if not j:
            continue
        eff = runtime_effective(j)
        for k, v in eff.items():
            row[f"{backend}_{k}"] = v
        row[f"{backend}_inconsistent_fields"] = ",".join(k for k, v in j.items() if "|" in v)
    if not recs.empty:
        lf = recs[recs.status == "load_failed"]
        row["models_ok"] = ",".join(m for m in MODELS if m in ok_models_all)
        row["models_load_failed"] = ",".join(sorted(set(lf.model)))
    # back-end-independent runtime values (taken from metal, cpu must agree)
    if row.get("metal_threads"):
        row["eff_threads_metal"] = row["metal_threads"]
        row["eff_threads_cpu"] = row.get("cpu_threads", "")
        row["eff_ngl_metal"] = row["metal_ngl"]
        row["eff_ngl_cpu"] = row.get("cpu_ngl", "")
        for k in ("n_batch", "n_ubatch", "flash_attn", "kv_type", "model_load", "no_kv_offload",
                  "split_mode", "embeddings", "backends"):
            a, b = row.get(f"metal_{k}", ""), row.get(f"cpu_{k}", "")
            row[f"eff_{k}"] = a if a == b else f"metal={a};cpu={b}"
        row["eff_poll"] = row.get("cpu_poll", "")
        row["eff_cpu_mask"] = row.get("cpu_cpu_mask", "")
        nopo = row.get("cpu_no_op_offload", "")
        # Before -nopo existed (< b5416) the Metal back end did not accept op offload
        # (offload_op absent or `return false` until b6556), so the cpu numbers were
        # CPU-only both with and without the flag.
        if nopo == "1" or (nopo == "" and row["build_number"] < 6556):
            row["eff_cpu_op_offload"] = "off"
        else:
            row["eff_cpu_op_offload"] = "on?"
    return row


def probe_arm_macros(flags: list[str]) -> str:
    """List the ``__ARM_FEATURE_*`` macros the compiler defines for a flag set.

    Args:
        flags: Compiler flags (and -D definitions) as used for the CPU back end.

    Returns:
        Comma-separated feature names, or 'n/a' when probing is disabled or fails.
    """
    if os.environ.get("STEP0_NO_COMPILER_PROBE") == "1":
        return "n/a"
    # The uv interpreter may run under Rosetta; a universal `cc` started from it would then
    # run as x86_64 (wrong default target, and -mcpu=native would see an x86 host).
    cmd = ["/usr/bin/arch", "-arm64", "cc", "-arch", "arm64", *flags, "-dM", "-E", "-x", "c", "/dev/null"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("compiler probe failed for %s: %s", flags, exc)
        return "n/a"
    if res.returncode != 0:
        logger.warning("compiler probe rc=%s for %s: %s", res.returncode, flags, res.stderr.strip()[:200])
        return "n/a"
    found = set(re.findall(r"#define __ARM_FEATURE_([A-Z0-9_]+) ", res.stdout))
    return ",".join(m for m in ARM_MACROS if m in found)


# --------------------------------------------------------------------------- change detection


@dataclass(frozen=True)
class ChangeSpec:
    """How a configuration column is interpreted when it changes.

    Attributes:
        column: effective_config.csv column.
        label: Human-readable label.
        kind: 'A' (runtime config/default), 'B' (build option) or 'info'.
        backends: 'cpu', 'metal' or 'both'.
        tests: 'pp', 'tg' or 'both'.
        expected: 'likely', 'possible' or 'unlikely' effect on throughput.
        note: Why (shown in config_changes.md).
    """

    column: str
    label: str
    kind: str
    backends: str
    tests: str
    expected: str
    note: str = ""


SPECS: tuple[ChangeSpec, ...] = (
    ChangeSpec("eff_threads_metal", "Thread count (metal back end, release default)", "A", "metal", "both", "likely"),
    ChangeSpec("eff_threads_cpu", "Thread count (cpu back end, explicit -t 8)", "A", "cpu", "both", "likely"),
    ChangeSpec("eff_ngl_metal", "-ngl (metal)", "A", "metal", "both", "likely"),
    ChangeSpec("eff_ngl_cpu", "-ngl (cpu)", "A", "cpu", "both", "likely"),
    ChangeSpec("eff_n_batch", "n_batch (logical batch)", "A", "both", "pp", "unlikely",
               "pp512 has only 512 tokens; with n_batch≥512 they are all processed in one batch"),
    ChangeSpec("eff_n_ubatch", "n_ubatch (physical batch, equal to n_batch in older releases without this option)",
               "A", "both", "pp", "likely"),
    ChangeSpec("eff_flash_attn", "flash_attn", "A", "both", "both", "likely",
               "With auto, the runtime decides per device whether to use Flash Attention"),
    ChangeSpec("eff_kv_type", "KV cache type K/V", "A", "both", "both", "likely"),
    ChangeSpec("eff_model_load", "Weight loading mode (mmap / direct-io / load-mode)", "A", "both", "both", "possible",
               "Decides whether weights are memory-mapped or read into a buffer, which may change the Metal buffer "
               "type and CPU memory access"),
    ChangeSpec("eff_poll", "Thread pool --poll", "A", "cpu", "both", "likely",
               "Appears together with the new thread pool implementation (cpu_mask/cpu_strict/poll), so the default "
               "and the implementation change are hard to separate"),
    ChangeSpec("eff_cpu_mask", "CPU affinity cpu_mask/cpu_strict", "A", "cpu", "both", "likely"),
    ChangeSpec("eff_cpu_op_offload", "cpu back end offloads large-batch matrix multiplications to Metal", "A", "cpu",
               "pp", "likely"),
    ChangeSpec("eff_no_kv_offload", "no_kv_offload", "A", "both", "both", "likely"),
    ChangeSpec("eff_split_mode", "split_mode", "A", "both", "both", "unlikely"),
    ChangeSpec("eff_embeddings", "embeddings", "A", "both", "both", "likely"),
    ChangeSpec("option_era", "CMake option scheme (llama → ggml subproject)", "B", "both", "both", "possible",
               "Build system reorganized: ggml became a separate subproject and compile definitions are set per target"),
    ChangeSpec("eff_arm_flags", "CPU architecture compile flags (-march/-mcpu)", "B", "cpu", "both", "likely",
               "Decides whether instructions such as i8mm/fp16/bf16/sme can be used in CPU kernels"),
    ChangeSpec("eff_accelerate", "Accelerate (GGML_USE_ACCELERATE)", "B", "cpu", "both", "likely"),
    ChangeSpec("eff_blas_backend", "BLAS back end (Accelerate)", "B", "cpu", "pp", "likely",
               "Large-batch matrix multiplications go to Accelerate; affects prompt processing only"),
    ChangeSpec("eff_llamafile", "llamafile SGEMM (tinyBLAS)", "B", "cpu", "pp", "possible",
               "tinyBLAS does not handle Q4_K/Q6_K weights and may affect only the f16/f32 attention matrix "
               "multiplications"),
    ChangeSpec("eff_openmp", "OpenMP threads", "B", "cpu", "both", "likely"),
    ChangeSpec("eff_cpu_repack", "CPU run-time weight repacking (GGML_CPU_AARCH64 / GGML_CPU_REPACK)", "B", "cpu", "both",
               "possible", "Repacked only Q4_0/IQ4_NL when introduced; later extensions to other types are "
               "implementation changes"),
    ChangeSpec("eff_kleidiai", "KleidiAI kernels", "B", "cpu", "both", "likely"),
    ChangeSpec("eff_metal_library", "Metal shader library source", "B", "metal", "both", "unlikely",
               "Both ways compile from .metal source at run time with the same compiler"),
    ChangeSpec("eff_metal_bf16", "GGML_METAL_USE_BF16", "B", "metal", "both", "unlikely",
               "None of the three models has bf16 tensors"),
    ChangeSpec("eff_metal_shader_debug", "Metal -fno-fast-math (SHADER_DEBUG)", "B", "metal", "both", "likely"),
    ChangeSpec("compiler", "Compiler", "B", "both", "both", "likely"),
    ChangeSpec("cmake", "CMake version", "B", "both", "both", "unlikely"),
    ChangeSpec("macos", "macOS version", "B", "both", "both", "likely"),
    ChangeSpec("eff_native_option", "LLAMA_NATIVE/GGML_NATIVE option value", "info", "cpu", "both", "unlikely",
               "The option is not the flags actually used; see eff_arm_flags for the flags on this machine"),
    ChangeSpec("eff_backends", "Back-end list reported by llama-bench", "info", "both", "both", "unlikely",
               "Field format change"),
    ChangeSpec("bench_src_dir", "llama-bench source directory", "info", "both", "both", "unlikely"),
    ChangeSpec("linked_libs_nonsystem", "Non-system dynamic libraries", "info", "both", "both", "unlikely",
               "OpenSSL is used only for downloading and is not on the inference path"),
    ChangeSpec("cfg_arm_feature_probe_failed", "CMake ARM feature probe failed (log only)", "info", "cpu", "both",
               "unlikely", "HAVE_* is used only for printing; the actual compile flags do not change"),
    ChangeSpec("help_n_gpu_layers", "--n-gpu-layers default", "info", "both", "both", "unlikely",
               "The pipeline always passes -ngl explicitly"),
    ChangeSpec("models_load_failed", "Models that failed to load", "info", "both", "both", "unlikely",
               "A change in model support, not in performance"),
)


def detect_changes(df: pd.DataFrame) -> pd.DataFrame:
    """Find change points of every spec'd column between consecutive tags with values.

    Args:
        df: effective_config rows sorted by build_number.

    Returns:
        One row per change (change_id, column, prev_tag, tag, old, new, spec fields).
    """
    # Columns where '' is a real value ("none"); the second item says which tags carry it.
    empty_ok = {"models_load_failed": "ok", "linked_libs_nonsystem": "ok", "cfg_arm_feature_probe_failed": "all"}
    rows: list[dict[str, Any]] = []
    for spec in SPECS:
        if spec.column not in df.columns:
            continue
        prev_tag, prev_val = None, None
        for _, r in df.iterrows():
            val = str(r[spec.column]) if pd.notna(r[spec.column]) else ""
            if spec.column in empty_ok:
                if empty_ok[spec.column] == "ok" and r["status"] != "ok":
                    continue
            elif val == "":
                continue
            if prev_val is not None and val != prev_val:
                rows.append({
                    "column": spec.column, "label": spec.label, "kind": spec.kind,
                    "prev_tag": prev_tag, "tag": r["tag"],
                    "prev_build": int(prev_tag[1:]), "build": int(r["build_number"]),
                    "old": prev_val, "new": val, "backends": spec.backends, "tests": spec.tests,
                    "expected": spec.expected, "note": spec.note,
                })
            prev_tag, prev_val = r["tag"], val
    ch = pd.DataFrame(rows)
    if ch.empty:
        return ch
    ch = ch.sort_values(["build", "kind", "column"]).reset_index(drop=True)
    ch.insert(0, "change_id", [f"K{i + 1:02d}" for i in range(len(ch))])
    by_tag = df.set_index("tag")
    details = []
    for _, c in ch.iterrows():
        d = ""
        if c["column"] == "eff_arm_flags":
            d = (f"ARM macros: {by_tag.at[c['prev_tag'], 'eff_arm_macros']} → {by_tag.at[c['tag'], 'eff_arm_macros']}; "
                 f"source: {by_tag.at[c['tag'], 'eff_arm_flags_source']}")
        details.append(d)
    ch["detail"] = details
    return ch


# --------------------------------------------------------------------------- build failures


def git_meta(args: list[str]) -> str:
    """Run a metadata-only git command on repo/ with lazy fetch and transports disabled.

    Args:
        args: git arguments after ``git -C repo``.

    Returns:
        stdout ('' on any failure).
    """
    if not (REPO / ".git").is_dir():
        return ""
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
    cmd = ["git", "-C", str(REPO), "-c", "protocol.allow=never", *args]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("git %s failed: %s", args[:2], exc)
        return ""
    return res.stdout if res.returncode == 0 else ""


def first_tag_containing(commit: str) -> str:
    """Smallest ``b<N>`` tag containing ``commit`` (from local refs only)."""
    out = git_meta(["tag", "--contains", commit])
    nums = sorted(int(t[1:]) for t in out.split() if re.fullmatch(r"b\d+", t))
    return f"b{nums[0]}" if nums else ""


def build_failure_section(df: pd.DataFrame) -> list[str]:
    """Markdown lines explaining the build failures and the minimal patch.

    Args:
        df: effective_config rows.

    Returns:
        Lines of markdown.
    """
    failed = df[df.status == "build_failed"]
    lines = ["## Tags that failed to build and a minimal patch (not built)", ""]
    if failed.empty:
        return lines + ["None.", ""]
    lines += ["| tag | Error line (cmake_build.log) | scripts/build-info.cmake | RESULT_VARIABLE check |", "|---|---|---|---|"]
    for _, r in failed.iterrows():
        log = read_text(RESULTS / r["tag"] / "cmake_build.log")
        errs = [ln.strip() for ln in log.splitlines() if " error: " in ln]
        code = ""
        for i, ln in enumerate(log.splitlines()):
            if " error: " in ln:
                nxt = log.splitlines()[i + 1:i + 2]
                # clang prints "1199 |     fprintf(...)"; drop the gutter so the markdown table stays intact
                code = re.sub(r"^\d+\s*\|\s*", "", nxt[0].strip()) if nxt else ""
                break
        err = re.sub(r"^.*/src/b\d+/", "", errs[0]) if errs else "?"
        lines.append(f"| {r['tag']} | `{err}` → `{code}` | sha256 {r['src_build_info_sha12']} | "
                     f"{r['src_build_info_guarded']} |")
    lines.append("")
    neigh = df[df.src_build_info_guarded.isin(["yes", "no"])][["tag", "build_number", "status",
                                                               "src_build_info_sha12", "src_build_info_guarded"]]
    last_failed = int(failed.build_number.max())
    window = neigh[neigh.build_number <= last_failed]
    window = pd.concat([window, neigh[neigh.build_number > last_failed].head(1)])
    lines += ["The same file in the failed tags and in the tags around them (tarballs read only):", "",
              "| tag | Build result | build-info.cmake sha256 (first 12 digits) | Return-code check |", "|---|---|---|---|"]
    for _, w in window.iterrows():
        lines.append(f"| {w['tag']} | {w['status']} | {w['src_build_info_sha12']} | {w['src_build_info_guarded']} |")
    lines.append("")
    lines += [
        ("**Cause**: this is not a clang incompatibility. `scripts/build-info.cmake` is identical in the three tags "
        "(sha256 equal in the first 12 digits). After finding git it runs `set(BUILD_NUMBER ${COUNT})` without checking "
        "that `git rev-list` succeeded. The source comes from a release tarball (no `.git`) and this machine has "
        "`/usr/bin/git` (configure log: `Found Git`, `fatal: not a git repository`), so COUNT is empty, `BUILD_NUMBER` "
        "is cleared, the generated `build-info.h` contains `#define BUILD_NUMBER ` (empty), and "
        "`fprintf(..., BUILD_NUMBER)` reports `expected expression`. The same macro is used in "
        "`examples/llama-bench/llama-bench.cpp` (`test::build_number = BUILD_NUMBER`), so compilation after common.cpp "
        "would fail for the same reason."),
        "",
        ("**Evidence**: the tags in the table above that build all have a return-code check (b1137/b1245 use "
        "`GIT_HEAD_RESULT`/`GIT_COUNT_RESULT`, later releases use `RESULT_VARIABLE RES` + `if (RES EQUAL 0)`), while "
        "the same file in the three failed tags has none."),
    ]
    log_out = git_meta(["log", "--format=%h|%ad|%s", "--date=short", "b1245..b1505", "--",
                        "scripts/build-info.cmake", "common/build-info.cpp.in", "scripts/build-info.h.in"])
    if log_out.strip():
        lines += ["", "Commits in the local `repo/` (git metadata read only) between b1245..b1505 that change build-info:", "",
                  "| Commit | Date | Description | First tag containing it |", "|---|---|---|---|"]
        for ln in log_out.strip().splitlines():
            h, d, s = ln.split("|", 2)
            lines.append(f"| {h} | {d} | {s.replace('|', '/')} | {first_tag_containing(h)} |")
        lines += ["", ("So one of the two commits after b1245 removed the check and the last commit restored it. "
                  "Affected are all releases between those two points that are built from a tarball on a machine with "
                  "git (the three failed tags are among them).")]
    lines += [
        "",
        "**Minimal patch (the same for the three tags, restores the check logic of b1245)**, applied to `src/<tag>/scripts/build-info.cmake`:",
        "",
        "```diff",
        "@@ if(Git_FOUND)",
        "     execute_process(",
        "         COMMAND ${GIT_EXECUTABLE} rev-parse --short HEAD",
        "         WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}",
        "         OUTPUT_VARIABLE HEAD",
        "         OUTPUT_STRIP_TRAILING_WHITESPACE",
        "+        RESULT_VARIABLE GIT_HEAD_RESULT",
        "     )",
        "     execute_process(",
        "         COMMAND ${GIT_EXECUTABLE} rev-list --count HEAD",
        "         WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}",
        "         OUTPUT_VARIABLE COUNT",
        "         OUTPUT_STRIP_TRAILING_WHITESPACE",
        "+        RESULT_VARIABLE GIT_COUNT_RESULT",
        "     )",
        "-    set(BUILD_COMMIT ${HEAD})",
        "-    set(BUILD_NUMBER ${COUNT})",
        "+    if(GIT_HEAD_RESULT EQUAL 0 AND GIT_COUNT_RESULT EQUAL 0)",
        "+        set(BUILD_COMMIT ${HEAD})",
        "+        set(BUILD_NUMBER ${COUNT})",
        "+    endif()",
        " endif()",
        "```",
        "",
        ("Effect: BUILD_NUMBER stays at its default 0 and BUILD_COMMIT at `unknown`, matching what the binaries of the "
        "other tags report (build_number_reported = 0 in records.csv). Only the build script changes, not the inference "
        "code, so performance stays comparable."),
        "",
        ("**Equivalent approach without changing the source**: between configure and build, add the number to the "
        "generated header (without `.git` no rule to regenerate it is registered, so the build does not overwrite it):"),
        "",
        "```bash",
        "sed -i '' 's/^#define BUILD_NUMBER $/#define BUILD_NUMBER 0/' src/<tag>/build-info.h",
        "```",
        "",
        ("**Before a re-run**: the patch is not verified (nothing was built). With the same toolchain b1245 and b1505 "
        "compile, and the ggml and llama targets finish before the point of failure, so this is expected to be the only "
        "blocker. A new error after patching would need its own fix. A re-run should follow build_bench.sh (REPS=5, "
        "PARAM_SETS=main) and record the patch in the build_meta of the tag (`patch` key) for traceability."),
        "",
    ]
    return lines


# --------------------------------------------------------------------------- report


def write_markdown(df: pd.DataFrame, ch: pd.DataFrame, path: Path) -> None:
    """Write config_changes.md.

    Args:
        df: effective_config rows.
        ch: change rows.
        path: Output path.
    """
    n = len(df)
    measured = df[df.status == "ok"]
    lines = [
        "# Step 0: effective configuration and configuration changes",
        "",
        (f"Generated by `scripts/analysis/step0_effective_config.py`; {n} tags ({len(measured)} measured, "
        f"{(df.status == 'build_failed').sum()} failed to build). Per-tag details are in `effective_config.csv`, and "
        "machine-readable configuration changes in `config_changes.csv` (step 1 uses it to classify events)."),
        "",
        ("Columns: `A` = change of the runtime configuration or of a default (the parameters llama-bench actually ran "
        "with), `B` = change of a build option (CMake options, compile flags, dependencies), `info` = recorded only, no "
        "effect on throughput expected. `Expected effect` is a prior judgment of the effect on throughput "
        "(likely/possible/unlikely). Step 1 classifies events with the likely/possible A/B changes only."),
        "",
    ]
    for kind, title in (("A", "Class A: runtime configuration / default changes"), ("B", "Class B: build-option changes"),
                        ("info", "Recorded only (info)")):
        sub = ch[ch.kind == kind] if not ch.empty else ch
        lines += [f"## {title} ({len(sub)})", ""]
        if sub.empty:
            lines += ["None.", ""]
            continue
        lines += ["| # | Interval (previous tag → this tag) | Item | Old value → new value | Back end/test | Expected effect | Note |",
                  "|---|---|---|---|---|---|---|"]
        for _, c in sub.iterrows():
            old = str(c["old"]).replace("|", "/")
            new = str(c["new"]).replace("|", "/")
            note = "; ".join(x for x in (c["note"], c["detail"]) if x)
            lines.append(f"| {c['change_id']} | {c['prev_tag']} → {c['tag']} | {c['label']} | `{old}` → `{new}` | "
                         f"{c['backends']}/{c['tests']} | {c['expected']} | {note} |")
        lines.append("")
    const_cols = [s for s in SPECS if s.column in df.columns]
    const_lines = []
    for s in const_cols:
        vals = df[s.column].dropna().astype(str)
        vals = vals[vals != ""]
        if len(vals) and vals.nunique() == 1:
            const_lines.append(f"- {s.label}: `{vals.iloc[0]}` (tags: {len(vals)})")
    lines += ["## Items constant over the 81 tags", ""] + const_lines + [""]
    lines += [
        "## CPU compile flags and actual ARM features on this machine (by interval)",
        "",
        "| Interval | Flags (source) | __ARM_FEATURE_* actually defined by the compiler |",
        "|---|---|---|",
    ]
    seg_start = None
    prev = None
    rows = list(df.itertuples())
    for i, r in enumerate(rows):
        key = (r.eff_arm_flags, r.eff_arm_macros)
        if prev is None:
            seg_start, prev = r, key
        if key != prev:
            last = rows[i - 1]
            lines.append(f"| {seg_start.tag} to {last.tag} | `{prev[0]}` ({seg_start.eff_arm_flags_source}) | {prev[1]} |")
            seg_start, prev = r, key
    if prev is not None:
        lines.append(f"| {seg_start.tag} to {rows[-1].tag} | `{prev[0]}` ({seg_start.eff_arm_flags_source}) | {prev[1]} |")
    lines += [
        "",
        ("Note: the ARM feature macros were measured with `cc <flags> -dM -E -x c /dev/null` (preprocessing only, no "
        "compilation). Without flags Apple clang targets apple-m1 by default: DOTPROD and FP16 vector arithmetic are "
        "available, i8mm (MATMUL_INT8) and BF16 are not. `-march=armv8.2a+dotprod+i8mm` turns on i8mm but drops FP16 "
        "vector arithmetic. `-mcpu=native+...` has all three."),
        "",
    ]
    lines += build_failure_section(df)
    lines += [
        "## Method and limitations",
        "",
        ("- The runtime configuration comes from records.csv and the raw JSON (values actually used). The `help_*` "
        "columns are the defaults the binary declares in `--help`. The two sources corroborate each other."),
        ("- Build-option defaults come from interpreting a subset of the CMake files in the tarball (APPLE, arm64, "
        "AppleClang, with check results taken from the configure log). Uncertain values carry `?`. From b4318 on the CPU "
        "flags are set inside a CMake function, so the flags printed in the configure log are used directly."),
        ("- The `eff_*` columns normalize equivalent settings (for example, without a type_k field f16_kv=true is "
        "recorded as f16/f16, without n_ubatch it equals n_batch, and mmap=1,dio=0 and load_mode=mmap are both recorded "
        "as mmap), so only real changes of the effective configuration are listed."),
        "- A configuration change can be located only between two adjacent sampled tags (sparse sampling).",
        "",
    ]
    path.write_text("\n".join(lines))


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--tags-file", type=Path, default=TAGS_FILE)
    ap.add_argument("--no-compiler-probe", action="store_true", help="do not run cc -dM -E")
    ap.add_argument("-v", "--verbose", action="store_true")
    ns = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if ns.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    if ns.no_compiler_probe:
        os.environ["STEP0_NO_COMPILER_PROBE"] = "1"
    tags = [t.strip() for t in ns.tags_file.read_text().split() if t.strip()]
    tags.sort(key=lambda t: int(t[1:]))
    macros: dict[str, str] = {}
    rows = []
    for tag in tags:
        rows.append(extract_tag(tag, macros))
        logger.info("%s: status=%s arm=%s", tag, rows[-1]["status"], rows[-1]["eff_arm_flags"])
    df = pd.DataFrame(rows).sort_values("build_number").reset_index(drop=True)
    ch = detect_changes(df)
    ns.out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(ns.out_dir / "effective_config.csv", index=False)
    ch.to_csv(ns.out_dir / "config_changes.csv", index=False)
    write_markdown(df, ch, ns.out_dir / "config_changes.md")
    counts = ch.kind.value_counts().to_dict() if not ch.empty else {}
    logger.info("wrote %d tags, %d change points %s -> %s", len(df), len(ch), counts, ns.out_dir)


if __name__ == "__main__":
    main()
