from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Risk
from .forms import RiskForm

from django.db.models import Q

@login_required
def risk_register(request):
    """
    Risk Register view displaying risks for user's projects.
    """
    user = request.user
    if user.is_superuser or user.is_staff:
        risks = Risk.objects.all().order_by('-risk_score')
    else:
        q = Q(project__owner=user) | Q(project__tasks__assignee=user)
        user_teams = list(user.teams.values_list('id', flat=True))
        if user_teams:
            q |= Q(project__teams__in=user_teams)
        risks = Risk.objects.filter(q).distinct().order_by('-risk_score')
        
    return render(request, 'risks/register.html', {'risks': risks})

@login_required
def risk_create(request):
    """
    View for creating a new risk.
    """
    if request.method == 'POST':
        form = RiskForm(request.POST)
        if form.is_valid():
            risk = form.save(commit=False)
            risk.created_by = request.user
            risk.save()
            return redirect('risks_register')
    else:
        form = RiskForm()
    
    return render(request, 'risks/form.html', {'form': form})
