from kw_engine.verify import run_checks, Verdict
from kw_engine.store.markdown import scan_memory_dir


def test_clean_corpus_passes(sample_memory):
    papers, principles = scan_memory_dir(sample_memory)
    verdicts = run_checks(papers, principles)
    fails = [v for v in verdicts if v.status == "FAIL"]
    # sample_memory has dangling link P-0002 which doesn't exist
    assert any("P-0002" in v.message for v in fails)


def test_counter_invariant_pass(sample_memory):
    papers, principles = scan_memory_dir(sample_memory)
    verdicts = run_checks(papers, principles)
    counter_checks = [v for v in verdicts if "counter" in v.check_name]
    assert all(v.status == "PASS" for v in counter_checks)
