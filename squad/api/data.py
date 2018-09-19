import json
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden, HttpResponseBadRequest


from squad.core import models
from squad.core.queries import get_metric_data
from squad.http import auth


def export_csv(results):
    lines = []
    for metric, data in results.items():
        for environment, entries in data.items():
            for entry in entries:
                line = [metric, environment] + entry
                lines.append(",".join(['"' + str(f) + '"' for f in line]))
    return "\n".join(lines)


@auth
def get(request, group_slug, project_slug):
    group = get_object_or_404(models.Group, slug=group_slug)
    project = get_object_or_404(group.projects, slug=project_slug)

    metrics = request.GET.getlist('metric')
    environments = request.GET.getlist('environment')

    results = get_metric_data(project, metrics, environments)

    fmt = request.GET.get('format', 'json')
    if fmt == 'json':
        return HttpResponse(
            json.dumps(results),
            content_type='application/json; charset=utf-8'
        )
    elif fmt == 'csv':
        return HttpResponse(
            export_csv(results),
            content_type='test/csv; charset=utf-8'
        )
    else:
        return HttpResponseBadRequest("Invalid format: %s" % fmt)
