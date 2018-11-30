import logging
import pytest
import time

from stacklight_tests.clients.fixtures import *  # noqa


logger = logging.getLogger(__name__)


@pytest.fixture
def destructive(request):
    """Does some recovering and cleaning actions provided
    by test in case of fail only.
    """
    recovery_actions = []
    yield recovery_actions
    rep_call = getattr(request.node, "rep_call", None)
    if rep_call is not None and rep_call.failed:
        for recovery_method in recovery_actions:
            try:
                recovery_method()
                # Add sleep to wait the operation is completed
                time.sleep(10)
            except Exception as e:
                logger.error(
                    "Recovery failed: {} with exception: {}".format(
                        recovery_method, e))
