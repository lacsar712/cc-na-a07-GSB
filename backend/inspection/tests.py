from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from inspection.models import ComparisonSheet, Inspection
from inspection.rules import judge


def make_inspection(code, measured, required=1200, bearing=0.4, by="keeper"):
    verdict, note = judge(measured, required, bearing)
    return Inspection.objects.create(
        aid_code=code,
        measured_cd=measured,
        required_cd=required,
        bearing_error_deg=bearing,
        verdict=verdict,
        note=note,
        created_by=by,
    )


class ComparisonSheetTests(TestCase):
    """对照单：留存、只读限制、来源变动。"""

    @classmethod
    def setUpTestData(cls):
        group = Group.objects.create(name="inspector")
        cls.keeper = User.objects.create_user(username="keeper", password="light123456")
        cls.keeper.groups.add(group)
        cls.watch = User.objects.create_user(username="watch", password="watch123456")
        # 明亮种子 / 偏暗种子，光强差 600
        cls.bright = make_inspection("LH-01", 1400, bearing=0.4)
        cls.dim = make_inspection("LH-09", 800, bearing=0.2)

    def login(self, user, password):
        self.client.force_login(user)

    def create_sheet(self):
        return self.client.post(
            reverse("sheet_create"),
            {"first_id": self.bright.pk, "second_id": self.dim.pk},
        )

    def test_create_stores_server_computed_diffs(self):
        self.login(self.keeper, "light123456")
        response = self.create_sheet()
        sheet = ComparisonSheet.objects.get()
        self.assertRedirects(response, reverse("sheet_detail", args=[sheet.pk]))
        # 差数在留存时写入存档
        self.assertEqual(sheet.brightness_diff, 600)
        self.assertAlmostEqual(sheet.bearing_diff, 0.2)
        self.assertEqual((sheet.first_code, sheet.second_code), ("LH-01", "LH-09"))
        self.assertEqual((sheet.first_verdict, sheet.second_verdict), ("合格", "不合格"))
        self.assertEqual(sheet.created_by, "keeper")
        # 详情页直接展示存档差数
        detail = self.client.get(reverse("sheet_detail", args=[sheet.pk]))
        self.assertContains(detail, "600")
        self.assertNotContains(detail, "来源已变动")

    def test_readonly_can_browse_but_not_create(self):
        self.login(self.keeper, "light123456")
        self.create_sheet()
        sheet = ComparisonSheet.objects.get()
        self.client.force_login(self.watch)
        # 能翻对照单册、打开旧单
        self.assertEqual(self.client.get(reverse("sheet_list")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("sheet_detail", args=[sheet.pk])).status_code, 200
        )
        # 不能新开：入口与直接提交都被拒
        response = self.client.get(reverse("sheet_create"))
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            reverse("sheet_create"),
            {"first_id": self.bright.pk, "second_id": self.dim.pk},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ComparisonSheet.objects.count(), 1)
        # 也不能改正实测
        self.assertEqual(
            self.client.get(reverse("edit", args=[self.dim.pk])).status_code, 403
        )

    def test_sheet_keeps_archived_diff_after_source_corrected(self):
        self.login(self.keeper, "light123456")
        self.create_sheet()
        sheet = ComparisonSheet.objects.get()
        self.assertFalse(sheet.source_changed)
        # 随后只改其中一笔的亮度
        self.client.post(
            reverse("edit", args=[self.dim.pk]),
            {
                "aid_code": "LH-09",
                "measured_cd": "950",
                "required_cd": "1200",
                "bearing_error_deg": "0.2",
            },
        )
        sheet.refresh_from_db()
        # 旧单仍显示留存时的差，并标明来源已变动
        self.assertEqual(sheet.brightness_diff, 600)
        self.assertTrue(sheet.second_changed)
        self.assertFalse(sheet.first_changed)
        self.assertTrue(sheet.source_changed)
        detail = self.client.get(reverse("sheet_detail", args=[sheet.pk]))
        self.assertContains(detail, "来源已变动")
        self.assertContains(detail, "600")
        # 册子上也标得出
        listing = self.client.get(reverse("sheet_list"))
        self.assertContains(listing, "来源已变动")

    def test_filter_by_aid_code(self):
        self.login(self.keeper, "light123456")
        self.create_sheet()
        other = make_inspection("LH-20", 1300)
        self.client.post(
            reverse("sheet_create"),
            {"first_id": self.bright.pk, "second_id": other.pk},
        )
        response = self.client.get(reverse("sheet_list"), {"code": "LH-09"})
        sheets = list(response.context["sheets"])
        self.assertEqual(len(sheets), 1)
        self.assertEqual(sheets[0].second_code, "LH-09")
        response = self.client.get(reverse("sheet_list"), {"code": "LH-01"})
        self.assertEqual(len(list(response.context["sheets"])), 2)
        response = self.client.get(reverse("sheet_list"), {"code": "NONE"})
        self.assertEqual(len(list(response.context["sheets"])), 0)

    def test_cannot_compare_same_inspection(self):
        self.login(self.keeper, "light123456")
        response = self.client.post(
            reverse("sheet_create"),
            {"first_id": self.bright.pk, "second_id": self.bright.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "两条实测不能是同一条")
        self.assertEqual(ComparisonSheet.objects.count(), 0)

    def test_login_required(self):
        self.assertRedirects(
            self.client.get(reverse("sheet_list")),
            f"{reverse('login')}?next={reverse('sheet_list')}",
        )
