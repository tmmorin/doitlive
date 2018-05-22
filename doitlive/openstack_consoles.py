from code import InteractiveConsole

from cliff import interactive

from openstackclient import shell as openstack_shell

from doitlive.keyboard import magictype


class CommandQueue(object):

    def __init__(self, commands, speed):
        self.commands = commands
        self.speed = speed

    def pop(self, idx):
        command = self.commands.pop(idx)
        magictype(command, prompt_template='(openstack)', speed=self.speed)
        return command


class OpenstackPlayerConsole(openstack_shell.OpenStackShell):

    def __init__(self, commands=None, speed=1, *args, **kwargs):
        super(OpenstackPlayerConsole, self).__init__()

        def interactive_app_factory(*args):
            interpreter = interactive.InteractiveApp(*args)
            interpreter.cmdqueue = CommandQueue(commands, speed)
            return interpreter

        self.interactive_app_factory = interactive_app_factory


def start_openstack_player(commands, speed=1):
    OpenstackPlayerConsole(commands=commands, speed=speed).run([])
