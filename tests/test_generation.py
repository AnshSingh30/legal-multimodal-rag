from rag.generation import NO_ANSWER_PHRASE, _extract_citations, _is_grounded


def test_extract_citations_parses_tag() -> None:
    answer = "Alice scored 90 [Citation: doc_id=abc123, page=1]."
    assert _extract_citations(answer) == {("abc123", "1")}


def test_extract_citations_handles_multiple_and_none() -> None:
    answer = (
        "Fact one [Citation: doc_id=abc123, page=1]. "
        "Fact two [Citation: doc_id=def456, page=2]."
    )
    assert _extract_citations(answer) == {("abc123", "1"), ("def456", "2")}
    assert _extract_citations("No citations here.") == set()


def test_is_grounded_accepts_no_answer_phrase_without_citation() -> None:
    assert _is_grounded(NO_ANSWER_PHRASE, valid_keys=set())


def test_is_grounded_requires_citation_subset_of_valid_keys() -> None:
    valid_keys = {("abc123", "1")}
    assert _is_grounded("Answer [Citation: doc_id=abc123, page=1].", valid_keys)
    assert not _is_grounded("Answer [Citation: doc_id=zzz, page=9].", valid_keys)
    assert not _is_grounded("Answer with no citation at all.", valid_keys)
