"""Two people selling the last pair of a size at the same moment.

The sale is one conditional UPDATE (quantity = quantity - 1 WHERE quantity > 0). On
PostgreSQL the second UPDATE waits for the first one's row lock, then re-checks the
condition against the committed row. SQLite runs one write at a time, so it can't show
this; the test only runs against PostgreSQL:

    DATABASE_URL=postgres://user:password@localhost:5432/db DJANGO_DEBUG=1 python manage.py test
"""
import threading
import time
from unittest import skipUnless

from django.db import connection, connections, transaction
from django.test import TransactionTestCase

from . import services
from .models import Batch, Sale, SizeEntry


def run_in_thread(target):
    """Start `target` on its own database connection; the returned join() re-raises its errors."""
    errors = []

    def wrapper():
        try:
            target()
        except Exception as error:  # noqa: BLE001 - handed back to the test thread
            errors.append(error)
        finally:
            connections.close_all()

    thread = threading.Thread(target=wrapper)
    thread.start()

    def join():
        thread.join(timeout=10)
        if thread.is_alive():
            raise AssertionError('thread did not finish')
        if errors:
            raise errors[0]

    return join


def wait_for_lock_wait(timeout=5):
    """Return once another connection is blocked on a lock, so the race really happened."""
    deadline = time.monotonic() + timeout
    with connection.cursor() as cursor:
        while time.monotonic() < deadline:
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'"
            )
            if cursor.fetchone()[0]:
                return
            time.sleep(0.02)
    raise AssertionError('the second sale never waited for the first one')


@skipUnless(connection.vendor == 'postgresql', 'row locks need PostgreSQL')
class LastPairTests(TransactionTestCase):
    def setUp(self):
        batch = Batch.objects.create(brand='Nike Air', bought_price=250_000)
        self.entry = SizeEntry.objects.create(batch=batch, size='42', quantity=1, initial_quantity=1)

    def sell(self, results):
        entry = SizeEntry.objects.get(pk=self.entry.pk)  # each counter has its own copy
        try:
            services.sell_one(entry, 300_000)
            results.append('sold')
        except services.OutOfStock:
            results.append('out of stock')

    def test_last_pair_is_sold_once(self):
        first_sold, finish_first = threading.Event(), threading.Event()
        first, second = [], []

        def first_counter():
            # Sell, then keep the transaction open so the second sale has to wait for it.
            with transaction.atomic():
                self.sell(first)
                first_sold.set()
                if not finish_first.wait(timeout=10):
                    raise AssertionError('test never released the first sale')

        join_first = run_in_thread(first_counter)
        self.assertTrue(first_sold.wait(timeout=10))
        join_second = run_in_thread(lambda: self.sell(second))
        try:
            wait_for_lock_wait()
        finally:
            finish_first.set()
        join_first()
        join_second()

        self.assertEqual((first, second), (['sold'], ['out of stock']))
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.quantity, 0)
        self.assertEqual(Sale.objects.count(), 1)
