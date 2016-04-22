# coding=utf8

import os
import unittest
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--shell',
                    action='store_true',
                    dest='shell',
                    default=False,
                    help="embed ipython shell"),
    )

    def handle(self, *args, **kwargs):
        """功能测试
        python manage.py ft --settings="settings.pro_settings" --shell
        --shell 进入ipython shell, 详细见tests/shelltest.py
        """
        shell = kwargs['shell']
        testsdir = os.path.join(settings.BASE_DIR, "tests")
        if not shell:
            unittest.main(argv=["", "discover", "-s", testsdir])
        else:
            unittest.main(argv=["", "discover", "-s", testsdir, "-p", "shell*.py"])
