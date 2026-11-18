from assayfold import licenses


def test_cc0_allowed_everywhere():
    for purpose in licenses.PURPOSES:
        assert licenses.gate("CC0-1.0", purpose)[0]


def test_non_commercial_blocked_for_commercial_and_samples():
    assert not licenses.gate("CC-BY-NC-4.0", "train_commercial")[0]
    assert not licenses.gate("CC-BY-NC-4.0", "redistribute_sample")[0]
    assert licenses.gate("CC-BY-NC-4.0", "train_research")[0]


def test_unknown_or_missing_blocked():
    assert not licenses.gate("", "rag")[0]
    assert not licenses.gate("Proprietary", "train_research")[0]


def test_share_alike_is_flagged():
    ok, why = licenses.gate("CC-BY-SA-4.0", "train_commercial")
    assert ok and "share-alike" in why


def test_eval_only_never_trains(nc_item, mol):
    assert not licenses.allowed(nc_item, "train_research")[0]
    assert licenses.allowed(mol, "train_research")[0]
