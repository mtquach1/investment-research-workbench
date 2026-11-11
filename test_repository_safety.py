import json
import subprocess
import zipfile
from pathlib import Path
import pytest
from repository_safety import audit_repository, export_public_source, forbidden_path, scan_content


@pytest.mark.parametrize('path',['.env','.env.local','nested/.env.production','.streamlit/secrets.toml',
    'output/private.json','data_cache/prices.json','personal.sqlite3','nested/auth.key',
    '.aws/credentials','private_exports/holdings.json'])
def test_private_paths_are_never_public_candidates(path):
    assert forbidden_path(path)


def test_safe_configuration_and_reference_cases_are_allowed():
    for path in ['.env.example','.github/workflows/ci.yml','.streamlit/config.toml',
                 'data/financial_reference_cases.json','docs/privacy-boundaries.md']:
        assert not forbidden_path(path)


def test_scanner_never_returns_matched_values():
    secret='fixture-private-'+'z'*32
    body=('ordinary line\nAPI_KEY='+secret+'\n').encode()
    findings=scan_content(body,known_private=[secret])
    assert findings and all(item.line==2 for item in findings)
    assert secret not in json.dumps([item.__dict__ for item in findings])
    token='ghp_'+'a'*36
    assert any(item.rule=='provider_token' for item in scan_content(token.encode()))
    assert not scan_content(b'https://example.com/news/sk-hynix-signs-a-research-agreement')
    assert scan_content(('sk-'+'c'*48).encode())


def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True).stdout


def repo(tmp_path):
    git(tmp_path,'init')
    git(tmp_path,'config','user.name','Synthetic Test')
    git(tmp_path,'config','user.email','test@example.com')
    (tmp_path/'.gitignore').write_text('.env\noutput/\n',encoding='utf-8')
    (tmp_path/'app.py').write_text('print("synthetic example")\n',encoding='utf-8')
    git(tmp_path,'add','.gitignore','app.py');git(tmp_path,'commit','-m','Synthetic baseline')
    return tmp_path


def test_new_repository_can_be_audited_before_its_first_commit(tmp_path):
    git(tmp_path,'init')
    (tmp_path/'app.py').write_text('print("synthetic example")\n')
    report=audit_repository(tmp_path)
    assert report.passed and report.history_blobs_scanned==0


def test_audit_refuses_to_inherit_a_parent_repository(tmp_path):
    root=repo(tmp_path);child=root/'child';child.mkdir()
    with pytest.raises(ValueError):audit_repository(child)


def test_export_omits_credentials_caches_and_git_history(tmp_path):
    root=repo(tmp_path)
    (root/'.env').write_text('OPENAI_API_KEY=fixture-private-value-123456\n',encoding='utf-8')
    (root/'output').mkdir();(root/'output/private.json').write_text('{"holding":123}')
    report=audit_repository(root)
    assert report.passed and report.history_blobs_scanned>=2
    archive=export_public_source(root,root/'output/public.zip')
    with zipfile.ZipFile(archive) as handle:
        assert 'app.py' in handle.namelist()
        assert not any(forbidden_path(name) or name.startswith('.git/') for name in handle.namelist())


def test_ignored_but_already_tracked_private_file_blocks_export(tmp_path):
    root=repo(tmp_path);(root/'.env').write_text('OPENAI_API_KEY=fixture-private-value-123456')
    git(root,'add','-f','.env')
    report=audit_repository(root)
    assert not report.passed and any(item.rule=='private_path' for item in report.findings)
    with pytest.raises(ValueError):export_public_source(root,root/'output/public.zip')


def test_deleted_secret_is_still_detected_in_reachable_history(tmp_path):
    root=repo(tmp_path);token='ghp_'+'b'*36
    (root/'old.py').write_text('TOKEN="'+token+'"')
    git(root,'add','old.py');git(root,'commit','-m','Synthetic bad history')
    git(root,'rm','old.py');git(root,'commit','-m','Delete synthetic secret')
    report=audit_repository(root)
    assert not report.passed and any(item.scope=='history' for item in report.findings)
    assert token not in json.dumps(report.to_dict())
    # Exporting a clean current tree is distinct from publishing private history.
    assert report.source_snapshot_passed
    archive=export_public_source(root,root/'output/clean.zip')
    with zipfile.ZipFile(archive) as handle:assert 'old.py' not in handle.namelist()


def test_symlinks_and_sensitive_known_values_fail_closed(tmp_path):
    root=repo(tmp_path);secret='fixture-private-'+'k'*32
    (root/'.env').write_text('ALPACA_SECRET_KEY='+secret)
    (root/'notes.md').write_text(secret)
    report=audit_repository(root)
    assert not report.passed and any(item.rule=='local_private_value' for item in report.findings)
