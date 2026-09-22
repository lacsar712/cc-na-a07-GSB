from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import ComparisonSheet, Inspection
from inspection.rules import judge


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def health(_request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "service": "nav-aid-inspection"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    from django.contrib.auth import authenticate, login

    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "用户名或密码错误"
        else:
            login(request, user)
            return redirect("list")
    return render(request, "login.html", {"error": error})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return redirect("login")


@login_required
def list_view(request):
    rows = Inspection.objects.all()
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    return render(request, "detail.html", {"row": row})


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error})


@login_required
@require_http_methods(["GET", "POST"])
def edit_view(request, pk):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可改正巡检记录")
    row = get_object_or_404(Inspection, pk=pk)
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            row.aid_code = code
            row.measured_cd = measured
            row.required_cd = required
            row.bearing_error_deg = bearing
            row.verdict = verdict
            row.note = note
            row.save()
            return redirect("detail", pk=row.pk)
    return render(request, "edit.html", {"error": error, "row": row})


@login_required
def sheet_list_view(request):
    sheets = ComparisonSheet.objects.all()
    code = request.GET.get("code", "").strip()
    if code:
        sheets = sheets.filter(Q(left_code__icontains=code) | Q(right_code__icontains=code))
    return render(request, "sheets.html", {"sheets": sheets, "code": code})


@login_required
@require_http_methods(["GET", "POST"])
def sheet_create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可留存对照单")
    error = ""
    if request.method == "POST":
        left = Inspection.objects.filter(pk=request.POST.get("left_id", "")).first()
        right = Inspection.objects.filter(pk=request.POST.get("right_id", "")).first()
        if left is None or right is None:
            error = "请选择两条实测记录"
        elif left.pk == right.pk:
            error = "两条实测不能是同一条"
        else:
            sheet = ComparisonSheet.objects.create(
                left=left,
                right=right,
                left_code=left.aid_code,
                right_code=right.aid_code,
                left_measured_cd=left.measured_cd,
                right_measured_cd=right.measured_cd,
                left_bearing_deg=left.bearing_error_deg,
                right_bearing_deg=right.bearing_error_deg,
                left_verdict=left.verdict,
                right_verdict=right.verdict,
                cd_diff=abs(left.measured_cd - right.measured_cd),
                bearing_diff=abs(left.bearing_error_deg - right.bearing_error_deg),
                created_by=request.user.username,
            )
            return redirect("sheet_detail", pk=sheet.pk)
    inspections = Inspection.objects.all()
    return render(request, "sheet_form.html", {"error": error, "inspections": inspections})


@login_required
def sheet_detail_view(request, pk):
    sheet = get_object_or_404(ComparisonSheet, pk=pk)
    return render(request, "sheet_detail.html", {"sheet": sheet})
