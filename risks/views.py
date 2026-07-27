from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Risk
from .forms import RiskForm

from django.db.models import Q
from django.shortcuts import get_object_or_404




@login_required
def risks_register(request):

    risks = Risk.objects.select_related(
        'project',
        'owner'
    ).all().order_by('-created_at')

    return render(
        request,
        'risks/register.html',
        {
            'risks': risks
        }
    )

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





@login_required
def risk_detail(request, pk):
    risk = get_object_or_404(Risk, pk=pk)

    return render(request, "risks/detail.html", {
        "risk": risk
    })


@login_required
def risk_update(request, pk):
    risk = get_object_or_404(Risk, pk=pk)

    if request.method == "POST":
        form = RiskForm(request.POST, instance=risk)

        if form.is_valid():
            form.save()
            return redirect("risk_detail", pk=risk.pk)

    else:
        form = RiskForm(instance=risk)

    return render(request, "risks/form.html", {
        "form": form
    })
@login_required
def risk_delete(request, id):

    risk = get_object_or_404(Risk, id=id)

    if request.method == "POST":
        risk.delete()
        return redirect('risks_register')

    return render(
        request,
        'risks/risk_confirm_delete.html',
        {
            'risk': risk
        }
    )