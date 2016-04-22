
# coding=utf8

from base import FunctionalTest
from const import ADMIN_DEFAULT_UID


class ShellTest(FunctionalTest):

    def setUp(self):
        # login
        super(ShellTest, self).setUp()
        self.create_pre_authenticated_session(ADMIN_DEFAULT_UID)

    def test_shell(self):
        """嵌入ipython shell"""
        def make_context():
            return dict(test=self, self=self)
        context = make_context()
        banner = ''
        # Try IPython
        try:
            try:
                # 0.10x
                from IPython.shell import IPShellEmbed
                ipshell = IPShellEmbed(banner=banner)
                ipshell(global_ns=dict(), local_ns=context)
            except ImportError:
                # 0.12+
                from IPython import embed
                embed(banner1=banner, user_ns=context)
            return
        except ImportError:
            pass
        # Use basic python shell
        import code
        code.interact(banner, local=context)
