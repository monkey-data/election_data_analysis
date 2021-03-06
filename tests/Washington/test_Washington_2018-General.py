import election_data_analysis as e


def test_data_exists(dbname):
    assert e.data_exists("2018 General", "Washington", dbname=dbname)


def test_wa_statewide_totals_18(dbname):
    assert (
        e.contest_total(
            "2018 General",
            "Washington",
            "US Senate WA",
            dbname=dbname,
        )
        == 3086168
    )


def test_wa_senate_totals_18(dbname):
    assert (
        e.contest_total(
            "2018 General",
            "Washington",
            "WA Senate District 13",
            dbname=dbname,
        )
        == 38038
    )


def test_wa_house_totals_18(dbname):
    assert (
        e.contest_total(
            "2018 General",
            "Washington",
            "WA House District 9",
            dbname=dbname,
        )
        == 52909
    )
