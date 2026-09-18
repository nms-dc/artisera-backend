import os
from invoke import task


@task
def pep8(ctx):
    msg = "PEP8 Check PASSED"
    cmd = "docker-compose exec backend pycodestyle backend/backend/apps --max-line-length=140 --exclude='*/migrations/'"
    ctx.run(cmd, pty=True)
    print(msg)


@task
def coverage(ctx):
    msg = "Coverage finished!"
    cmd = [
        "docker-compose exec backend coverage run --source='.' manage.py test",
        "docker-compose exec backend coverage report --omit='*migrations*'",
        "docker-compose exec backend coverage html"
    ]

    for c in cmd:
        ctx.run(c, pty=True)
    print(msg)

@task
def fixture(ctx, app_name):
    cmd = f'docker-compose exec backend python manage.py loaddata backend/backend/apps/{app_name}/fixtures/*.json'
    ctx.run(cmd, pty=True)