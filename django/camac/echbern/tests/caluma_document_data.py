# These dicts contain a parsed example Document. In contrast to
# `ech_bern.data_preparation.{slugs_baugesuch,slugs_vorabklaerung_einfach}`, these
# dicts contain the german label of *Choices.
# If you find yourself editing this file, you might also want to edit
# `slugs_baugesuch`.

from ..data_preparation import AnswersDict

baugesuch_data = AnswersDict(
    **{
        "anzahl-abstellplaetze-fur-motorfahrzeuge": 23,
        "caluma-workflow-slug": "building-permit",
        "baukosten-in-chf": 232323,
        "bemerkungen": "Foo bar",
        "beschreibung-bauvorhaben": "Beschreibung&#10;Mehr Beschreibung",
        "beschreibung-der-prozessart-tabelle": [{"prozessart": "Fliesslawine"}],
        "dauer-in-monaten": 23,
        "ech-subject": "Generelles Baugesuch",
        "effektive-geschosszahl": 23,
        "gemeinde": "2",
        "geplanter-baustart": "2019-09-15",
        "gwr-egid": "23",
        "nr": "23",
        "nutzungsart": ["Wohnen"],
        "nutzungszone": "Testnutzungszone",
        "ort-grundstueck": "Burgdorf",
        "ort-parzelle": "Burgdorf",
        "parzelle": [
            AnswersDict(
                {
                    "e-grid-nr": "23",
                    "lagekoordinaten-nord": "1070500.000",
                    "lagekoordinaten-ost": "2480034.0",
                    "parzellennummer": "1586",
                }
            ),
            AnswersDict(
                {
                    "e-grid-nr": "24",
                    "lagekoordinaten-nord": "1070600.000",
                    "lagekoordinaten-ost": "2480035.0",
                    "parzellennummer": "1587",
                }
            ),
        ],
        "personalien-gesuchstellerin": [
            AnswersDict(
                {
                    "name-gesuchstellerin": "Smith",
                    "nummer-gesuchstellerin": "23",
                    "ort-gesuchstellerin": "Burgdorf",
                    "plz-gesuchstellerin": 2323,
                    "strasse-gesuchstellerin": "Teststrasse",
                    "vorname-gesuchstellerin": "Winston",
                    "juristische-person-gesuchstellerin": "Nein",
                    "name-juristische-person-gesuchstellerin": None,
                }
            )
        ],
        "personalien-grundeigentumerin": [
            AnswersDict(
                {
                    "name-grundeigentuemerin": "Smith",
                    "nummer-grundeigentuemerin": "23",
                    "ort-grundeigentuemerin": "Burgdorf",
                    "plz-grundeigentuemerin": 2323,
                    "strasse-grundeigentuemerin": "Teststrasse",
                    "vorname-grundeigentuemerin": "Winston",
                    "juristische-person-grundeigentuemerin": "Nein",
                    "name-juristische-person-grundeigentuemerin": None,
                }
            )
        ],
        "personalien-projektverfasserin": [
            AnswersDict(
                {
                    "name-projektverfasserin": "Smith",
                    "nummer-projektverfasserin": None,
                    "ort-projektverfasserin": "Burgdorf",
                    "plz-projektverfasserin": 2323,
                    "strasse-projektverfasserin": "Teststrasse",
                    "vorname-projektverfasserin": "Winston",
                    "juristische-person-projektverfasserin": "Nein",
                    "name-juristische-person-projektverfasserin": None,
                }
            )
        ],
        "personalien-vertreterin-mit-vollmacht": [
            AnswersDict(
                {
                    "name-vertreterin": "Smith",
                    "nummer-vertreterin": "23",
                    "ort-vertreterin": "Burgdorf",
                    "plz-vertreterin": 2323,
                    "strasse-vertreterin": "Teststrasse",
                    "vorname-vertreterin": "Winston",
                    "juristische-person-vertreterin": "Ja",
                    "name-juristische-person-vertreterin": "Firma XY AG",
                }
            )
        ],
        "sammelschutzraum": "Ja",
        "strasse-flurname": "Teststrasse",
    }
)

vorabklaerung_data = {
    "beschreibung-bauvorhaben": "lorem ipsum mit tab",
    "caluma-workflow-slug": "preliminary-clarification",
    "ech-subject": "Einfache Vorabklärung",
    "gemeinde": "2",
    "gwr-egid": "23",
    "name-gesuchstellerin": "Smith",
    "nr": "23",
    "ort-grundstueck": "Burgdorf",
    "strasse-flurname": "Teststrasse mit Leerzeichen",
}
