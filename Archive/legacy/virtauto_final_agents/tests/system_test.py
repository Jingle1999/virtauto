import os

def test_guardian_rules_present():
    assert os.path.exists('rules/guardian.yaml')

def test_seo_checklist_present():
    assert os.path.exists('rules/seo-checklist.yaml')

def test_site_audit_workflow_has_lighthouse():
    data = open('.github/workflows/site-audit.yml','r',encoding='utf-8').read()
    assert 'lhci' in data or 'lighthouse' in data

def test_content_ingest_script_exists():
    assert os.path.exists('scripts/content_ingest.py')
