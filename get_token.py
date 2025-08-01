import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from Authentication import Command

if __name__ == '__main__':
    command = Command()
    command.handle()