"""Redacted publication checks and a source-only export. No credential output."""
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

PRIVATE_DIRS={'.git','.aws','.ssh','.codex','.agents','.venv','venv','__pycache__',
    '.pytest_cache','node_modules','output','tmp','data_cache','private_exports','local_exports','.vscode'}
PRIVATE_SUFFIXES={'.pem','.key','.pfx','.p12','.sqlite','.sqlite3','.db','.log','.pdf','.xlsx','.parquet'}
PRIVATE_NAMES={'credentials.json','token.json','secrets.toml','frozen-paper-basket.json',
    'stock-decision-snapshot.json','experimental-stock-decisions.json','experimental-monthly-contribution.json'}
TOKEN=re.compile(r'(?:sk-(?:(?:proj|svcacct)-[A-Za-z0-9_-]{32,}|[A-Za-z0-9]{40,})|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16})')
EMAIL=re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
PERSONAL_PATH=re.compile(r'(?:[A-Za-z]:\\+Users\\+[^\\\s<>]+|/(?:Users|home)/[^/\s<>]+)')


def forbidden_path(name):
    path=PurePosixPath(name.replace('\\','/'));parts=[part.lower() for part in path.parts]
    base=path.name.lower()
    return (any(part in PRIVATE_DIRS for part in parts) or base in PRIVATE_NAMES
        or (base.startswith('.env') and base!='.env.example') or path.suffix.lower() in PRIVATE_SUFFIXES
        or base.endswith(('-wal','-shm')) or base.startswith('private-')
        or '..' in parts or path.is_absolute())


@dataclass(frozen=True)
class ContentFinding:
    rule: str
    line: int


def scan_content(payload, *, known_private=()):
    if b'\x00' in payload:
        return [ContentFinding('binary_requires_review',1)]
    try:text=payload.decode('utf-8-sig')
    except UnicodeDecodeError:return [ContentFinding('encoding_requires_review',1)]
    findings=[]
    for number,line in enumerate(text.splitlines(),1):
        rules=set()
        if any(value and value in line for value in known_private):rules.add('local_private_value')
        if TOKEN.search(line):rules.add('provider_token')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',line):rules.add('private_key')
        if re.search(r'\b[a-z]+://[^\s/:]+:[^\s/@]+@',line):rules.add('url_credentials')
        if PERSONAL_PATH.search(line):rules.add('personal_machine_path')
        for address in EMAIL.findall(line):
            domain=address.rsplit('@',1)[1].lower()
            if domain not in {'example.com','example.org','example.net','users.noreply.github.com'} and not domain.endswith(('.test','.invalid')):
                rules.add('contact_address')
        findings.extend(ContentFinding(rule,number) for rule in sorted(rules))
    return findings


def _git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True).stdout


def _private_values(root):
    values=[]
    # Compare exact local values internally. Neither values nor their hashes are emitted.
    path=root/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            key,sep,value=line.partition('=')
            if sep and not key.lstrip().startswith('#') and re.search(r'KEY|TOKEN|SECRET|PASSWORD|SEC_USER_AGENT',key,re.I):
                value=value.strip().strip('\"\'')
                if len(value)>=8:
                    values.append(value)
                    values.extend(EMAIL.findall(value))
    return values


@dataclass(frozen=True)
class RepositoryFinding:
    scope: str
    path: str
    rule: str
    line: int = 0


@dataclass
class RepositoryAudit:
    candidate_paths: list[str] = field(default_factory=list)
    findings: list[RepositoryFinding] = field(default_factory=list)
    history_blobs_scanned: int = 0
    history_contact_metadata_present: bool = False

    @property
    def passed(self):return not self.findings

    @property
    def source_snapshot_passed(self):return not any(item.scope=='worktree' for item in self.findings)

    def to_dict(self):return dict(passed=self.passed,source_snapshot_passed=self.source_snapshot_passed,**asdict(self))


def audit_repository(root):
    root=Path(root).resolve()
    actual_root=Path(_git(root,'rev-parse','--show-toplevel').decode('utf-8').strip()).resolve()
    if actual_root!=root:raise ValueError('Initialize Git in the exact source folder before auditing it')
    known=_private_values(root);report=RepositoryAudit()
    candidates=_git(root,'ls-files','--cached','--others','--exclude-standard','-z').decode('utf-8').split('\x00')
    for name in sorted(set(filter(None,candidates))):
        path=root/name
        if forbidden_path(name):
            report.findings.append(RepositoryFinding('worktree',name,'private_path'));continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            report.findings.append(RepositoryFinding('worktree',name,'unsafe_link'));continue
        if not path.exists():continue  # unstaged deletion: export the current tree, not old bytes
        if not path.is_file() or path.stat().st_size>3*1024*1024:
            report.findings.append(RepositoryFinding('worktree',name,'file_requires_review'));continue
        report.candidate_paths.append(name)
        report.findings.extend(RepositoryFinding('worktree',name,item.rule,item.line)
            for item in scan_content(path.read_bytes(),known_private=known))
    objects=_git(root,'rev-list','--objects','--all').decode('utf-8').splitlines()
    if not objects:return report  # a newly initialized repository has no history yet
    names=dict(item.partition(' ')[::2] for item in objects)
    if len(names)>10000:
        report.findings.append(RepositoryFinding('history','[history]','history_budget_requires_review'))
    else:
        encoded=('\n'.join(names)+'\n').encode()
        headers=subprocess.run(['git','-C',str(root),'cat-file','--batch-check'],input=encoded,
            check=True,capture_output=True).stdout.decode().splitlines()
        selected=[];total=0
        for header in headers:
            digest,kind,size=header.split();size=int(size)
            if kind!='blob':continue
            name=names[digest]
            if forbidden_path(name):report.findings.append(RepositoryFinding('history',name,'private_path'))
            total+=size
            if size>3*1024*1024 or total>64*1024*1024:
                report.findings.append(RepositoryFinding('history',name,'file_requires_review'));continue
            selected.append(digest)
        if selected:
            batch=subprocess.run(['git','-C',str(root),'cat-file','--batch'],
                input=('\n'.join(selected)+'\n').encode(),check=True,capture_output=True).stdout
            offset=0
            for expected in selected:
                end=batch.index(b'\n',offset)
                digest,kind,size=batch[offset:end].decode().split();size=int(size)
                if digest!=expected or kind!='blob':raise ValueError('Unexpected history object')
                payload=batch[end+1:end+1+size];offset=end+size+2
                report.history_blobs_scanned+=1
                report.findings.extend(RepositoryFinding('history',names[digest],issue.rule,issue.line)
                    for issue in scan_content(payload,known_private=known))
    metadata=_git(root,'log','--all','--format=%ae%n%ce').decode('utf-8')
    report.history_contact_metadata_present=any(item.rule=='contact_address' for item in scan_content(metadata.encode()))
    return report


def export_public_source(root, archive):
    root=Path(root).resolve();archive=Path(archive).resolve()
    if not archive.is_relative_to(root/'output'):
        raise ValueError('Write the source export under the ignored output directory')
    report=audit_repository(root)
    if not report.source_snapshot_passed:raise ValueError('Source publication audit failed; no archive created')
    known=_private_values(root);payloads={}
    for name in report.candidate_paths:
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Source changed during export')
        payload=path.read_bytes()
        if scan_content(payload,known_private=known):raise ValueError('Source changed during export')
        payloads[name]=payload
    manifest={'format':'public-source-manifest-v1','git_history_included':False,
        'files':[{'path':name,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
            for name,payload in payloads.items()],
        'notice':'Source snapshot only. Pattern checks are not a guarantee that every secret or privacy issue is detectable.'}
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as handle:
        for name,payload in payloads.items():handle.writestr(name,payload)
        handle.writestr('PUBLIC_SOURCE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    return archive
