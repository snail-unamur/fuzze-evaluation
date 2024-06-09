# -*- coding: utf-8 -*-
import datetime as dt
from typing import Any
from unittest import SkipTest, skip
from fuzze import backup_tour, load_fuzz_data, test_tour_fuzze, make_backup_filesys
from fuzze.tours.fuzz_pickers import PickAll
from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger
import pathlib as path

import logging
from fuzze.tours.db import RollBackDB
from fuzze.tours.tracer import FuzzeTracer

# We assume that the test is run in a standard Odoo addon structure
ADDON_PATH = path.Path(__file__).parent.parent
TOUR_PATH = ADDON_PATH / "static" / "tests" / "tours"
GENERATED_PATH = TOUR_PATH / "generated"
FAILED_PATH = make_backup_filesys(ADDON_PATH)
REPORT_PATH = FAILED_PATH / "report"


@tagged("post_install", "-at_install", "fuzze")
class FuzzeMainFlowCase(HttpCase):

    def test_fuzze(self):
        col = load_fuzz_data(
            GENERATED_PATH / "fuzz_data.json",
        )
        tracer = FuzzeTracer(col)
        self.setup_main_flow()
        for tour_name in col.keys():
            with RollBackDB(self), self.subTest(msg=f"Fuzz {tour_name}"), mute_logger(
                "odoo.http"
            ):
                r = test_tour_fuzze(
                    self,
                    url_path="/web",
                    tour_name=tour_name,
                    login="admin",
                    logger=self._logger,
                    step_delay=300,
                    timeout=180,
                )
                if r is not None:
                    try:
                        backup_tour(
                            GENERATED_PATH / col[tour_name].filename,
                            FAILED_PATH / col[tour_name].filename,
                        )
                    except Exception as e:
                        self._logger.error("Error backing up tour: %s", e)
                    tracer.trace(*r)
        tracer.save(REPORT_PATH / f"report_{dt.datetime.now(dt.UTC).date()}.json")

    @skip("This test is used to find root cause of a bug found using Fuzze.")
    def test_main_flow(self):
        self.setup_main_flow()
        self.start_tour(
            "/web?debug=assets",
            "main_flow_tour",
            timeout=180,
            login="admin",
            step_delay=300,
            watch=True,
            debug=True,
        )

    def setup_main_flow(self):
        # Enable Make to Order
        order = self.env.ref("stock.route_warehouse0_mto")
        assert order is not None
        order.active = True
        # Define minimal accounting data to run without CoA
        a_expense = self.env["account.account"].create(
            {
                "code": "X2120",
                "name": "Expenses - (test)",
                "account_type": "expense",
            }
        )
        a_recv = self.env["account.account"].create(
            {
                "code": "X1012",
                "name": "Debtors - (test)",
                "reconcile": True,
                "account_type": "asset_receivable",
            }
        )
        a_pay = self.env["account.account"].create(
            {
                "code": "X1111",
                "name": "Creditors - (test)",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        a_sale = self.env["account.account"].create(
            {
                "code": "X2020",
                "name": "Product Sales - (test)",
                "account_type": "income",
            }
        )
        bnk = self.env["account.account"].create(
            {
                "code": "X1014",
                "name": "Bank Current Account - (test)",
                "account_type": "asset_cash",
            }
        )

        Property = self.env["ir.property"]
        Property._set_default(
            "property_account_receivable_id", "res.partner", a_recv, self.env.company
        )
        Property._set_default(
            "property_account_payable_id", "res.partner", a_pay, self.env.company
        )
        Property._set_default(
            "property_account_position_id", "res.partner", False, self.env.company
        )
        Property._set_default(
            "property_account_expense_categ_id",
            "product.category",
            a_expense,
            self.env.company,
        )
        Property._set_default(
            "property_account_income_categ_id",
            "product.category",
            a_sale,
            self.env.company,
        )

        self.expenses_journal = self.env["account.journal"].create(
            {
                "name": "Vendor Bills - Test",
                "code": "TEXJ",
                "type": "purchase",
                "refund_sequence": True,
            }
        )
        self.bank_journal = self.env["account.journal"].create(
            {
                "name": "Bank - Test",
                "code": "TBNK",
                "type": "bank",
                "default_account_id": bnk.id,
            }
        )
        self.sales_journal = self.env["account.journal"].create(
            {
                "name": "Customer Invoices - Test",
                "code": "TINV",
                "type": "sale",
                "default_account_id": a_sale.id,
                "refund_sequence": True,
            }
        )
