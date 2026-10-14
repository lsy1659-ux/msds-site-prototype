"""Recover declared release outputs on Python/IO failure; keep inputs untouched.

Each replacement uses a staged file on the destination filesystem. The group
is rolled back for caught exceptions. This is not a multi-file crash transaction:
an uncatchable process/power loss may leave recovery backups for manual recovery.
"""
from __future__ import annotations
import json,os,tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any,Iterable


def stage_bytes(target:Path,data:bytes,suffix:str='.tmp')->Path:
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=f'.{target.name}.msds-',suffix=suffix,dir=target.parent)
    staged=Path(name)
    try:
        with os.fdopen(fd,'wb')as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return staged


@contextmanager
def preserve_files(paths:Iterable[Path]):
    """Restore only the explicitly declared outputs if the enclosed work fails."""
    originals={};backups={};keep_backups=False
    try:
        for path in dict.fromkeys(Path(p).resolve()for p in paths):
            original=path.read_bytes()if path.exists()else None
            originals[path]=original
            if original is not None:backups[path]=stage_bytes(path,original,'.bak')
        try:
            yield
        except BaseException as error:
            failures=[]
            for path,original in originals.items():
                try:
                    if original is None:
                        path.unlink(missing_ok=True)
                    elif not path.exists()or path.read_bytes()!=original:
                        os.replace(backups[path],path)
                except OSError as restore_error:
                    failures.append(f'{path}: {restore_error}')
            if failures:
                keep_backups=True
                saved=', '.join(str(p)for p in backups.values()if p.exists())
                raise RuntimeError('Release rollback failed: '+'; '.join(failures)+'; recovery backups kept: '+saved)from error
            raise
    finally:
        if not keep_backups:
            for path in backups.values():path.unlink(missing_ok=True)


def write_json_pair(outputs:dict[Path,Any])->None:
    """Serialize and stage every JSON before replacing either existing output."""
    payloads={Path(path): (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')for path,data in outputs.items()}
    staged={}
    try:
        with preserve_files(payloads):
            for path,data in payloads.items():staged[path]=stage_bytes(path,data)
            for path,temp in staged.items():os.replace(temp,path)
    finally:
        for path in staged.values():path.unlink(missing_ok=True)
