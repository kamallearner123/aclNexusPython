from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Risk
from .forms import RiskForm

@login_required
def risk_register(request):
    """
    Risk Register view displaying all risks.
    """
    risks = Risk.objects.all().order_by('-risk_score')
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
