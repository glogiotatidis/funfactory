from functools import partial
import os
import shutil
import subprocess
from subprocess import check_call, Popen
import sys

from nose.plugins import Plugin

from funfactory import manage


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PLAYDOH = os.path.join(ROOT, '.playdoh', 'funtestapp')
shell = partial(check_call, shell=True)
DB_USER = os.environ.get('FF_DB_USER', 'root')
DB_PASS = os.environ.get('FF_DB_PASS', '')
DB_NAME = os.environ.get('FF_DB_NAME', '_funfactory_test')


def test_root():
    assert os.path.exists(os.path.join(ROOT, 'setup.py')), (
                    'This does not appear to be the root dir: %s' % ROOT)


class FunFactoryTests(Plugin):
    """Enables the fun factory test suite."""
    __test__ = False  # Nose: do not collect as test
    name = 'ff-tests'
    score = 999  # needs to execute early

    def options(self, parser, env=os.environ):
        super(FunFactoryTests, self).options(parser, env=env)
        self.parser = parser

    def configure(self, options, conf):
        super(FunFactoryTests, self).configure(options, conf)
        self.enabled = True  # Enables the plugin without a cmd line flag
        self.options = options

    def begin(selg):
        if not os.path.exists(PLAYDOH):
            container = os.path.abspath(os.path.join(PLAYDOH, '..'))
            if not os.path.exists(container):
                os.mkdir(container)
            check_call(['git', 'clone', '--recursive',
                        'git://github.com/mozilla/playdoh.git',
                        PLAYDOH])
        else:
            proj_sh = partial(shell, cwd=PLAYDOH)
            proj_sh('git pull origin base')
            proj_sh('git submodule sync -q')
            proj_sh('git submodule update --init')
            vend_sh = partial(shell, cwd=os.path.join(PLAYDOH, 'vendor'))
            vend_sh('git pull origin master')
            vend_sh('git submodule sync -q')
            vend_sh('git submodule update --init')

        st = os.path.join(PLAYDOH, 'settings_local.py')
        if os.path.exists(st):
            os.unlink(st)
        shutil.copy(os.path.join(PLAYDOH, 'settings_local.py-dist'),
                    st)

        with open(st, 'r') as f:
            new_st = f.read()
            new_st = new_st.replace("'USER': ''",
                                    "'USER': '%s'" % DB_USER)
            new_st = new_st.replace("'PASSWORD': ''",
                                    "'PASSWORD': '%s'" % DB_PASS)
            new_st = new_st.replace("'NAME': ''",
                                    "'NAME': '%s'" % DB_NAME)

        with open(st, 'w') as f:
            f.write(new_st)

        extra = ''
        if DB_PASS:
            extra = '--password=%s' % DB_PASS
        shell('mysql -u %s %s -e "create database if not exists %s"'
              % (DB_USER, extra, DB_NAME))
        check_call([sys.executable, 'manage.py', 'syncdb', '--noinput'],
                   cwd=PLAYDOH)

        # For in-process tests:
        manage.setup_environ(os.path.join(PLAYDOH, 'manage.py'))
        # Puts path back to this dev version of funfactory:
        sys.path.insert(0, ROOT)