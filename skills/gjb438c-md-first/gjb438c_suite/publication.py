"""Rollback-safe publication of a DOCX and its audit reports.

This is a serialized transaction for cooperating writers, not a filesystem-wide
atomic snapshot: consumers must validate report hashes. Process termination or
power loss leaves the lock/backups for operator recovery, never a success claim.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import warnings
from typing import Iterable, Mapping


class PublicationError(RuntimeError):
    pass


def distinct_paths(paths: Iterable[str | Path]) -> list[Path]:
    raw = [Path(p).absolute() for p in paths]
    if any(p.is_symlink() for p in raw):
        raise PublicationError("publication/input paths must not be symlinks")
    resolved = [p.resolve() for p in raw]
    if len(set(resolved)) != len(resolved):
        raise PublicationError("input and output paths must be distinct")
    present = [p for p in resolved if p.exists()]
    for i, a in enumerate(present):
        for b in present[i + 1:]:
            if a.samefile(b):
                raise PublicationError("input and output paths alias the same file")
    if any(p.exists() and not p.is_file() for p in resolved):
        raise PublicationError("input and output paths must be regular files")
    return resolved


def _fsync_file(path: Path) -> None:
    # Windows _commit/FlushFileBuffers requires a writable handle.
    # r+b does not truncate or change bytes, and remains valid on POSIX.
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())


def _fsync_dir(path: Path) -> None:
    # Windows does not support opening a directory with os.open. File flushes
    # still run there; directory-entry durability is not claimed on Windows.
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _locks(paths: list[Path]):
    acquired: list[Path] = []
    try:
        for target in sorted(paths):
            target.parent.mkdir(parents=True, exist_ok=True)
            token = hashlib.sha256(os.path.normcase(str(target)).encode()).hexdigest()[:24]
            lock = target.parent / f".gjb-publish-{token}.lock"
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as exc:
                raise PublicationError(f"publication locked; inspect before recovery: {lock}") from exc
            acquired.append(lock)
            try:
                os.write(fd, f"pid={os.getpid()} target={target}\n".encode())
                os.fsync(fd)
            finally:
                os.close(fd)
        yield
    finally:
        for lock in reversed(acquired):
            try:
                lock.unlink(missing_ok=True)
            except OSError as exc:
                warnings.warn(f"publication lock needs cleanup: {lock}: {exc}", RuntimeWarning)


def _temporary(target: Path, suffix: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=suffix, dir=target.parent)
    os.close(fd)
    return Path(name)


def publish_files(files: Mapping[Path, Path], *, marker: Path) -> None:
    """Stage every source, flush it, then replace reports and the DOCX last.

    The mapping is destination -> completed staged source. Never pass a live
    document as a staged source. A raised exception means no certification.
    """
    targets = distinct_paths(files)
    sources = [Path(files[raw]).resolve() for raw in files]
    distinct_paths([*targets, *sources])
    marker = Path(marker).resolve()
    if marker not in targets:
        raise PublicationError("publication marker must belong to the release set")
    if any(not s.is_file() or s.stat().st_size == 0 for s in sources):
        raise PublicationError("release set contains a missing or empty staged file")
    ordered = [p for p in targets if p != marker] + [marker]
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    published: list[Path] = []
    preserve: set[Path] = set()
    with _locks(targets):
        try:
            for target, source in zip(targets, sources):
                staged[target] = _temporary(target, ".stage")
                shutil.copyfile(source, staged[target])
                _fsync_file(staged[target])
                backup = _temporary(target, ".backup") if target.exists() else None
                backups[target] = backup
                if backup is not None:
                    shutil.copyfile(target, backup)
                    _fsync_file(backup)
                _fsync_dir(target.parent)
            for target in ordered:
                os.replace(staged[target], target)
                # Must be recorded BEFORE either durability check can fail.
                published.append(target)
                _fsync_file(target)
                _fsync_dir(target.parent)
        except BaseException as exc:
            rollback_errors = []
            for target in reversed(published):
                try:
                    backup = backups[target]
                    if backup is None:
                        target.unlink(missing_ok=True)
                    else:
                        os.replace(backup, target)
                    _fsync_dir(target.parent)
                except OSError as restore_error:
                    if backups.get(target) is not None:
                        preserve.add(backups[target])
                    rollback_errors.append(f"{target}: {restore_error}; backup={backups.get(target)}")
            detail = "; rollback needs operator recovery: " + "; ".join(rollback_errors) if rollback_errors else ""
            raise PublicationError(f"publication failed: {exc}{detail}") from exc
        finally:
            for temporary in [*staged.values(), *backups.values()]:
                if temporary is not None and temporary not in preserve:
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError as exc:
                        warnings.warn(f"publication temporary needs cleanup: {temporary}: {exc}", RuntimeWarning)


def write_report(path: str | Path, text: str, *, inputs: Iterable[str | Path] = ()) -> None:
    target = distinct_paths([path, *inputs])[0]
    with tempfile.TemporaryDirectory(prefix="gjb-report-") as folder:
        staged = Path(folder) / "report.json"
        staged.write_text(text, encoding="utf-8")
        publish_files({target: staged}, marker=target)
