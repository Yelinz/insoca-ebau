from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection

from camac.core.management.commands.dumpconfig import (
    models_referencing_data,
    pure_config_models,
)


class Command(BaseCommand):
    help = "Moves all responsibilities from source service to target service"

    queries = []

    def add_arguments(self, parser):
        parser.add_argument(
            "-s",
            "--source",
            type=str,
            dest="source",
            help="Source service PKs (comma-separated)",
            required=True,
        )
        parser.add_argument(
            "-t",
            "--target",
            type=int,
            dest="target",
            help="Target service PK",
            required=True,
        )
        parser.add_argument(
            "-e",
            "--execute",
            default=False,
            dest="exec",
            action="store_true",
            help="Directly execute the query instead of just printing it",
        )
        parser.add_argument(
            "-d",
            "--disable",
            default=False,
            dest="disable",
            action="store_true",
            help="Disable 'source' services",
        )

    @staticmethod
    def _get_all_service_foreign_keys():
        query = """select kcu.table_name as foreign_table,
                   string_agg(kcu.column_name, ';') as fk_columns
            from information_schema.table_constraints tco
            join information_schema.key_column_usage kcu
                      on tco.constraint_schema = kcu.constraint_schema
                      and tco.constraint_name = kcu.constraint_name
            join information_schema.referential_constraints rco
                      on tco.constraint_schema = rco.constraint_schema
                      and tco.constraint_name = rco.constraint_name
            join information_schema.table_constraints rel_tco
                      on rco.unique_constraint_schema = rel_tco.constraint_schema
                      and rco.unique_constraint_name = rel_tco.constraint_name
            where tco.constraint_type = 'FOREIGN KEY' AND rel_tco.table_name = 'SERVICE'
            group by kcu.table_name;"""
        with connection.cursor() as cursor:
            cursor.execute(query)
            return [row for row in cursor.fetchall()]

    def _get_query(self, table, column, source, target):
        return (
            f'UPDATE "{table}" SET "{column}" = {target} WHERE "{column}" = {source};'
        )

    def _filter(self, data):
        """Only change tables that handle `data`, not `configuration`."""
        config_tables = [
            apps.get_model(m)._meta.db_table
            for m in pure_config_models + models_referencing_data
        ]
        return [(table, cols) for table, cols in data if table not in config_tables]

    def handle(self, *args, **options):
        sources = options["source"].split(",")
        for source in sources:
            self.queries.append(f'\n-- source: {source}, target: {options["target"]}')
            for table, columns in self._filter(self._get_all_service_foreign_keys()):
                for column in columns.split(";"):
                    self.queries.append(
                        self._get_query(table, column, source, options["target"])
                    )

        if options["disable"]:
            self.queries.append("\n-- disable old services and groups")
            self.queries.append(
                f'UPDATE "SERVICE" SET "DISABLED"=1 WHERE "SERVICE_ID" IN ({options["source"]});'
            )
            self.queries.append(
                f'UPDATE "GROUP" SET "DISABLED"=1 WHERE "SERVICE_ID" IN ({options["source"]});'
            )

        queries = "\n".join(self.queries)

        self.stdout.write(queries)

        if options["exec"]:
            with connection.cursor() as cursor:
                cursor.execute(queries)
