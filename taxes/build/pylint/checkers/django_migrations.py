import astroid
from pylint.interfaces import IAstroidChecker
from pylint.checkers import BaseChecker

from taxes.build.pylint.checkers import BASE_ID


def _is_migrations_module(node):
    if not isinstance(node, astroid.Module):
        return False

    return '/migrations/' in node.file


class DjangoMigrationChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = 'taxes-django-migration'
    priority = -1
    msgs = {
        f'E{BASE_ID}01': (
            'Migration importing an application module',
            'migration-import-app',
            'Migration should avoid importing application modules',
        )
    }
    options = ()

    def __init__(self, linter=None):
        super().__init__(linter)
        self._is_migration = False

    def visit_module(self, node):
        self._is_migration = _is_migrations_module(node)

    def leave_module(self, node):  # pylint: disable=unused-argument
        self._is_migration = False

    def visit_import(self, node):
        self._inspect_import(node)

    def visit_import_from(self, node):
        self._inspect_import(node)

    def _inspect_import(self, node):
        if not self._is_migration:
            return

        for module_name, _ in node.names:
            if module_name.startswith('taxes') and module_name != 'taxes.receipts.models.fields':
                self.add_message(
                    'migration-import-app',
                    node=node,
                )


def register(linter):
    linter.register_checker(DjangoMigrationChecker(linter))
