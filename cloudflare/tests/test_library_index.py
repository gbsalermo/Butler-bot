from library_index import search


def test_character_lookup():
    results=search("quem é Walter White",domain="culture")
    assert results
    assert results[0]["name"]=="walter white"
    assert "Breaking Bad" in results[0]["summary"] or "breaking bad" in results[0]["summary"].lower()


def test_pop_culture_lookup():
    results=search("Jake Peralta",domain="culture")
    assert results
    assert results[0]["name"]=="jake peralta"


def test_game_filters_have_relevant_results():
    results=search("jogo leve coop pc",domain="games")
    assert results
    assert any("leve" in [str(x).lower() for x in r.get("tags",[])] or "coop" in [str(x).lower() for x in r.get("tags",[])] for r in results)


def test_book_filters():
    results=search("livro brasileiro classico",domain="books")
    assert results
    assert all(r["domain"]=="books" for r in results)


def test_philosophy_alias():
    results=search("Spinoza",domain="culture")
    assert results
    assert any("spinoza" in (r["name"]+" "+" ".join(str(x) for x in r.get("tags",[]))).lower() for r in results)


def test_butler_is_not_book_substring():
    results=search("oi butler",domain="books")
    assert not results
