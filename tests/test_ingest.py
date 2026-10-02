import pandas as pd
import config
from fitradar import ingest


def test_sizes_from_different_vendors_become_one_label():
    assert {ingest.normalise_size(v) for v in ["XL", "X-Large", "42", " xl "]} == {"XL"}
    assert ingest.normalise_size("Age 2") == "2Y"


def test_short_or_symbol_only_comments_are_unreadable():
    assert ingest.unreadable_by_rule("ok")
    assert ingest.unreadable_by_rule("")
    assert ingest.unreadable_by_rule("??")
    assert not ingest.unreadable_by_rule("size chota hai")
    assert not ingest.unreadable_by_rule("ढीला है बहुत")


def test_load_drops_duplicates_and_counts_add_up():
    comments, units, report = ingest.load(config.DATA_DIR / "comments.csv", config.DATA_DIR / "units_sold.csv")
    assert report["in_file"] == 2030 and report["dropped_duplicates"] == 30
    assert report["unreadable_rule"] + report["to_read"] == len(comments) == 2000
    assert set(comments["size"]) <= set(ingest.SIZE_ORDER)


def test_missing_columns_are_named(tmp_path):
    bad = tmp_path / "c.csv"; pd.DataFrame({"text": ["x"]}).to_csv(bad, index=False)
    try:
        ingest.load(bad, config.DATA_DIR / "units_sold.csv")
        assert False
    except ingest.BadFile as error:
        assert "comment_id" in str(error)
