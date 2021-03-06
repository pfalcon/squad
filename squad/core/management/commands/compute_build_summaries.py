import argparse
import logging

from datetime import timedelta, datetime
from django.core.management.base import BaseCommand
from django.utils import timezone

from squad.core.models import Project, Build, BuildSummary


logger = logging.getLogger()
environments_cache = {}


def valid_date(date):
    try:
        return datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        msg = "'{0}' is not a valid date.".format(
            date)
        raise argparse.ArgumentTypeError(msg)


def progress(show):
    if show:
        print('.', end='')


def __get_environments__(build, project):
    project_id = build.project_id
    if environments_cache.get(project_id) is None:
        environments_cache[project_id] = build.project.environments.all()
    return environments_cache[project_id]


class Command(BaseCommand):

    help = """Compute metric summaries per build per environment"""

    def add_arguments(self, parser):
        parser.add_argument('--project', help='Optionally, specify a project to compute, on the form $group/$project')
        parser.add_argument('--show-progress', action='store_true', help='Prints out one dot per build in stdout')
        parser.add_argument(
            '--start-date',
            dest="start_date",
            default=(datetime.now() - timedelta(days=180)),
            type=valid_date,
            help="Start date for project status updates (default: 6 months before current date, format: YYYY-MM-DD)."
        )
        parser.add_argument(
            '--end-date',
            dest="end_date",
            default=datetime.now(),
            type=valid_date,
            help="End date for project status updates (default: today, format: YYYY-MM-DD)."
        )

    def handle(self, *args, **options):
        start_date = timezone.make_aware(options['start_date'])
        end_date = timezone.make_aware(options['end_date'])
        project_name = options['project'] or False
        show_progress = options['show_progress']

        builds = Build.objects.filter(
            datetime__range=(start_date, end_date),
            status__finished=True
        )

        project = None
        if project_name:
            slugs = project_name.split('/')
            if len(slugs) != 2:
                logger.error('Project "%s" is malformed (should be group_slug/project_slug). Exiting...' % (project_name))
                return

            try:
                group_slug, project_slug = slugs
                project = Project.objects.get(group__slug=group_slug, slug=project_slug)
            except Project.DoesNotExist:
                logger.error('Project "%s" does not exist. Exiting...' % (project_name))
                return

            logger.info('Filtering builds from project "%s"' % (project_name))
            builds = builds.filter(project=project)

        logger.info('Computing metrics summary for %d builds' % (builds.count()))
        if show_progress:
            logger.info('Showing progress, one dot means one processed build')

        for build in builds.all():
            progress(show_progress)
            for environment in __get_environments__(build):
                BuildSummary.create_or_update(build, environment)
