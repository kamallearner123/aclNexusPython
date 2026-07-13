import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .agent import ProjectIntelligenceAgent, REPORT_PRESETS
from .forms import PIAAnalysisForm
from .permissions import pia_system_admin_required


@login_required
@pia_system_admin_required
def pia_home(request):
    result = None
    error = None

    if request.method == 'POST':
        form = PIAAnalysisForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.cleaned_data.get('project')
            try:
                result = ProjectIntelligenceAgent(request.user).analyze(
                    prompt=form.cleaned_data.get('prompt'),
                    report_type=form.cleaned_data.get('report_type'),
                    project_id=project.pk if project else None,
                )
            except PermissionDenied as exc:
                error = str(exc)
            except Exception as exc:
                error = f"PIA could not complete the analysis: {exc}"
    else:
        form = PIAAnalysisForm(user=request.user)

    return render(request, 'ai_assistant/pia.html', {
        'form': form,
        'result': result,
        'error': error,
        'presets': REPORT_PRESETS,
    })


@login_required
@pia_system_admin_required
@require_POST
def pia_analyze_api(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        result = ProjectIntelligenceAgent(request.user).analyze(
            prompt=payload.get('prompt', ''),
            report_type=payload.get('report_type') or 'project_health',
            project_id=payload.get('project_id'),
        )
        return JsonResponse({
            'title': result.title,
            'executive_summary': result.executive_summary,
            'findings': result.findings,
            'recommendations': result.recommendations,
            'sections': result.sections,
            'trace': result.trace,
            'tool_outputs': result.tool_outputs,
            'generation_mode': result.generation_mode,
            'llm_error': result.llm_error,
            'narrative': result.narrative,
        })
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)
