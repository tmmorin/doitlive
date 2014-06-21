# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import random
import getpass
from contextlib import contextmanager

import pytest
import click
from click import style
from click.testing import CliRunner

import doitlive
from doitlive import cli, TermString

random.seed(42)
HERE = os.path.abspath(os.path.dirname(__file__))

def random_string(n, alphabet='abcdefghijklmnopqrstuvwxyz1234567890;\'\\][=-+_`'):
    return ''.join([random.choice(alphabet) for _ in range(n)])

@pytest.fixture(scope='session')
def runner():
    doitlive.TESTING = True
    return CliRunner()

def run_session(runner, filename, user_input):
    session = os.path.join(HERE, 'sessions', filename)
    # Press ENTER at beginning of session and ENTER twice at end
    user_in = ''.join(['\n', user_input, '\n\n'])
    return runner.invoke(cli, ['play', session], input=user_in)


class TestPlayer:

    def test_basic_session(self, runner):
        user_input = random_string(len('echo "Hello"'))
        result = run_session(runner, 'basic.session', user_input)

        assert result.exit_code == 0
        assert 'echo "Hello"' in result.output

    def test_session_with_unicode(self, runner):
        user_input = random_string(len(u'echo "H´l¬ø ∑ø®ld"'))
        result = run_session(runner, 'unicode.session', user_input)
        assert result.exit_code == 0

    def test_session_with_envvar(self, runner):
        user_input = random_string(len('echo $HOME'))

        result = run_session(runner, 'env.session', user_input)
        assert result.exit_code == 0
        assert os.environ['HOME'] in result.output

    def test_session_with_comment(self, runner):
        user_input = random_string(len('echo foo'))
        result = run_session(runner, 'comment.session', user_input)
        assert result.exit_code == 0
        assert 'foo' not in result.output, 'comment was not skipped'
        assert 'bar' in result.output

    def test_esc_key_aborts(self, runner):
        result = run_session(runner, 'basic.session', 'echo' + doitlive.ESC)
        assert result.exit_code > 0

    def test_pwd(self, runner):
        user_input = random_string(3)
        result = run_session(runner, 'pwd.session', user_input)
        assert os.getcwd() in result.output

    def test_custom_prompt(self, runner):
        user_input = random_string(len('echo'))
        result = run_session(runner, 'prompt.session', user_input)
        assert getpass.getuser() in result.output

    def test_custom_var(self, runner):
        user_input = random_string(len('echo $MEANING'))
        result = run_session(runner, 'envvar.session', user_input)
        assert '42' in result.output

    def test_custom_speed(self, runner):
        user_input = random_string(3)
        result = run_session(runner, 'speed.session', user_input)
        assert '123456789' in result.output


    def test_bad_theme(self, runner):
        result = runner.invoke(cli, ['-p', 'thisisnotatheme'])
        assert result.exit_code > 0


    def test_cd(self, runner):
        user_input = (random_string(len('cd ~')) + '\n' +
            random_string(len('pwd')) + '\n')
        result = run_session(runner, 'cd.session', user_input)

        assert result.exit_code == 0
        assert os.environ['HOME'] in result.output

    def test_cd_bad(self, runner):
        user_input = (random_string(len('cd /thisisnotadirectory')) + '\n' +
            random_string(len('pwd')) + '\n')
        result = run_session(runner, 'cd_bad.session', user_input)

        assert result.exit_code == 0


def test_themes_list(runner):
    result1 = runner.invoke(cli, ['themes'])
    assert result1.exit_code == 0
    result2 = runner.invoke(cli, ['themes', '--list'])
    result3 = runner.invoke(cli, ['themes', '-l'])
    assert result1.output == result2.output == result3.output

def test_themes_preview(runner):
    result1 = runner.invoke(cli, ['themes', '--preview'])
    assert result1.exit_code == 0
    result2 = runner.invoke(cli, ['themes', '-p'])
    assert result2.exit_code == 0
    assert result1.output == result2.output


def test_version(runner):
    result = runner.invoke(cli, ['--version'])
    assert doitlive.__version__ in result.output
    result2 = runner.invoke(cli, ['-v'])
    assert result.output == result2.output

class TestTermString:

    @pytest.fixture
    def ts(self):
        return TermString('foo')

    @pytest.fixture
    def ts_blank(self):
        return TermString('')

    def test_str(self, ts):
        assert str(ts) == 'foo'

    # Test all the ANSI colors provided by click
    @pytest.mark.parametrize('color', click.termui._ansi_colors)
    def test_color(self, color, ts):
        colored = getattr(ts, color)
        assert isinstance(colored, TermString)
        assert str(colored) == style('foo', fg=color)

    def test_bold(self, ts):
        assert str(ts.bold) == style('foo', bold=True)

    def test_blink(self, ts):
        assert str(ts.blink) == style('foo', blink=True)

    def test_dim(self, ts):
        assert str(ts.dim) == style('foo', dim=True)

    def test_underlined(self, ts):
        assert str(ts.underlined) == style('foo', underline=True)

    def test_paren(self, ts, ts_blank):
        assert str(ts.paren) == '(foo)'
        assert str(ts_blank.paren) == ''

    def test_square(self, ts, ts_blank):
        assert str(ts.square) == '[foo]'
        assert str(ts_blank.square) == ''

    def test_curly(self, ts, ts_blank):
        assert str(ts.curly) == '{foo}'
        assert str(ts_blank.curly) == ''


@contextmanager
def recording_session(runner, commands=None, args=None):
    commands = commands or ['echo "foo"']
    args = args or []

    with runner.isolated_filesystem():
        command_input = '\n'.join(commands)
        user_input = ''.join(['\n', command_input, '\nfinish\n'])
        runner.invoke(cli, ['record'] + args, input=user_input)
        yield

class TestRecorder:

    def test_record_creates_session_file(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ['record'], input='\necho "Hello"\nfinish\n')
            assert result.exit_code == 0, result.output
            assert os.path.exists('session.sh')

    def test_custom_output_file(self, runner):
        with recording_session(runner, args=['mysession.sh']):
            assert os.path.exists('mysession.sh')

    def test_record_content(self, runner):
        commands = ['echo "foo"', 'echo "bar"']
        with recording_session(runner, commands), open('session.sh') as fp:
            content = fp.read()
            assert 'echo "foo"\n' in content
            assert 'echo "bar"' in content

    def test_header_content(self, runner):
        with recording_session(runner), open('session.sh') as fp:
            content = fp.read()
            assert '#doitlive shell: /bin/bash' in content

    def test_custom_prompt(self, runner):
        with recording_session(runner, args=['-p', 'sorin']), open('session.sh') as fp:
            content = fp.read()
            assert '#doitlive prompt: sorin' in content

    def test_prompt_if_file_already_exists(self, runner):
        with runner.isolated_filesystem():
            # session.sh file already exists
            with open('session.sh', 'w') as fp:
                fp.write('foo')
            # runs "record" and enters "n" at the prompt
            result = runner.invoke(cli, ['record'], input='n\n')
            assert result.exit_code == 1
            assert 'Overwrite?' in result.output

    def test_cding(self, runner):
        with runner.isolated_filesystem():
            initial_dir = os.getcwd()
            cd_to = os.path.join(initial_dir, 'mydir')
            os.mkdir(cd_to)
            user_input = ''.join([
                '\n', 'cd mydir', '\n', 'pwd', '\n', '\nfinish\n'
            ])
            result = runner.invoke(cli, ['record'], input=user_input)
            assert result.exit_code == 0
            # cwd was reset
            assert os.getcwd() == initial_dir
            assert cd_to in result.output

    def test_session_file_cannot_be_a_directory(self, runner):
        with runner.isolated_filesystem():
            os.mkdir('mydir')
            result = runner.invoke(cli, ['record', 'mydir'])
            assert result.exit_code > 0
