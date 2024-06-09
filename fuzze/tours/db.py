from odoo.tests import HttpCase
from odoo.sql_db import Savepoint, TestCursor


class RollBackDB:
    def __init__(self, case: HttpCase):
        self.cr: TestCursor = case.env.cr  # type: ignore

    def __enter__(self) -> Savepoint:
        self.cs = self.cr.savepoint()
        return self.cs

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cs.rollback()
