# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['test_notify_completed_work_item[True-kt_bern] 1'] = [
    (
        'Aufgabe abgeschlossen (eBau-Nr. 2020-01 (1)) / tâche complétée (n° eBau 2020-01 (1))',
        '''Guten Tag

Die Aufgabe "Ingolf Säuberlich" im Dossier 2020-01 (1) wurde von User Admin (Justin Valdez) abgeschlossen.

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Sie erhalten diese Notifikation, weil Sie beim Erstellen der Aufgabe die Notifikationseinstellung "Bei Abschluss" gewählt haben.

*** version française ***

Bonjour,

La tâche "Ingolf Säuberlich" dans le dossier 2020-01 (1) a été terminée par User Admin (Justin Valdez).

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Vous recevez cette notification parce que vous avez sélectionné le paramètre de notification "après achèvement" lorsque vous avez créé la tâche.
''',
        [
            'imeyer@example.net'
        ],
        [
        ]
    ),
    (
        'Aufgabe abgeschlossen (eBau-Nr. 2020-01 (1)) / tâche complétée (n° eBau 2020-01 (1))',
        '''Guten Tag

Die Aufgabe "Ingolf Säuberlich" im Dossier 2020-01 (1) wurde von User Admin (Justin Valdez) abgeschlossen.

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Sie erhalten diese Notifikation, weil Sie beim Erstellen der Aufgabe die Notifikationseinstellung "Bei Abschluss" gewählt haben.

*** version française ***

Bonjour,

La tâche "Ingolf Säuberlich" dans le dossier 2020-01 (1) a été terminée par User Admin (Justin Valdez).

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Vous recevez cette notification parce que vous avez sélectionné le paramètre de notification "après achèvement" lorsque vous avez créé la tâche.
''',
        [
            'tiffany26@example.com'
        ],
        [
        ]
    ),
    (
        'Aufgabe abgeschlossen (eBau-Nr. 2020-01 (1)) / tâche complétée (n° eBau 2020-01 (1))',
        '''Guten Tag

Die Aufgabe "Ingolf Säuberlich" im Dossier 2020-01 (1) wurde von User Admin (Justin Valdez) abgeschlossen.

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Sie erhalten diese Notifikation, weil Sie beim Erstellen der Aufgabe die Notifikationseinstellung "Bei Abschluss" gewählt haben.

*** version française ***

Bonjour,

La tâche "Ingolf Säuberlich" dans le dossier 2020-01 (1) a été terminée par User Admin (Justin Valdez).

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Vous recevez cette notification parce que vous avez sélectionné le paramètre de notification "après achèvement" lorsque vous avez créé la tâche.
''',
        [
            'stevenbanks@example.net'
        ],
        [
        ]
    )
]

snapshots['test_notify_completed_work_item[True-kt_schwyz] 1'] = [
    (
        'Aufgabe abgeschlossen (Gesuchs-Nummer 72-21-001)',
        '''Guten Tag

Die Aufgabe "Karin Ehlert B.Eng." im Dossier 72-21-001 wurde von User Admin (Rebecca Gonzalez) abgeschlossen.

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Sie erhalten diese Notifikation, weil Sie beim Erstellen der Aufgabe die Notifikationseinstellung "Bei Abschluss" gewählt haben.
''',
        [
            'phyllis84@example.net'
        ],
        [
        ]
    ),
    (
        'Aufgabe abgeschlossen (Gesuchs-Nummer 72-21-001)',
        '''Guten Tag

Die Aufgabe "Karin Ehlert B.Eng." im Dossier 72-21-001 wurde von User Admin (Rebecca Gonzalez) abgeschlossen.

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Sie erhalten diese Notifikation, weil Sie beim Erstellen der Aufgabe die Notifikationseinstellung "Bei Abschluss" gewählt haben.
''',
        [
            'qabbott@example.com'
        ],
        [
        ]
    ),
    (
        'Aufgabe abgeschlossen (Gesuchs-Nummer 72-21-001)',
        '''Guten Tag

Die Aufgabe "Karin Ehlert B.Eng." im Dossier 72-21-001 wurde von User Admin (Rebecca Gonzalez) abgeschlossen.

http://ebau.local/index/redirect-to-instance-resource/instance-id/1

Sie erhalten diese Notifikation, weil Sie beim Erstellen der Aufgabe die Notifikationseinstellung "Bei Abschluss" gewählt haben.
''',
        [
            'thomas86@example.com'
        ],
        [
        ]
    )
]
