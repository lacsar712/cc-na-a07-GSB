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
    return render(request, "edit.html", {"row": row, "error": error})


@login_required
def sheet_list_view(request):
    code = request.GET.get("code", "").strip()
    sheets = ComparisonSheet.objects.all()
    if code:
        sheets = sheets.filter(Q(first_code__icontains=code) | Q(second_code__icontains=code))
    return render(request, "sheet_list.html", {"sheets": sheets, "code": code})


@login_required
@require_http_methods(["GET", "POST"])
def sheet_create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可留存对照单")
    error = ""
    if request.method == "POST":
        try:
            first = Inspection.objects.get(pk=int(request.POST["first_id"]))
            second = Inspection.objects.get(pk=int(request.POST["second_id"]))
        except (KeyError, ValueError, Inspection.DoesNotExist):
            error = "请选择两条实测"
        else:
            if first.pk == second.pk:
                error = "两条实测不能是同一条"
            else:
                # 差数在服务端算好并写入存档，页面只读存档值，不临时相减
                sheet = ComparisonSheet.objects.create(
                    first=first,
                    second=second,
                    first_code=first.aid_code,
                    second_code=second.aid_code,
                    first_verdict=first.verdict,
                    second_verdict=second.verdict,
                    first_measured_cd=first.measured_cd,
                    second_measured_cd=second.measured_cd,
                    first_required_cd=first.required_cd,
                    second_required_cd=second.required_cd,
                    first_bearing_error_deg=first.bearing_error_deg,
                    second_bearing_error_deg=second.bearing_error_deg,
                    brightness_diff=abs(first.measured_cd - second.measured_cd),
                    bearing_diff=abs(first.bearing_error_deg - second.bearing_error_deg),
                    created_by=request.user.username,
                )
                return redirect("sheet_detail", pk=sheet.pk)
    return render(
        request,
        "sheet_form.html",
        {"error": error, "inspections": Inspection.objects.all()},
    )


@login_required
def sheet_detail_view(request, pk):
    sheet = get_object_or_404(ComparisonSheet, pk=pk)
    return render(request, "sheet_detail.html", {"sheet": sheet})
