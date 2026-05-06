# Generated manually — mavjud bazada defaultlar bo'lmasa, 22+ ustuniyat kategoriya

from django.db import migrations


DEFAULT_CATEGORIES = [
    # ---------- Xarajat (22+) ----------
    ("expense", "ovqat-ichimlik"),
    ("expense", "tushlik"),
    ("expense", "transport"),
    ("expense", "taksi"),
    ("expense", "kommunal"),
    ("expense", "internet-aloqa"),
    ("expense", "uy-ijara"),
    ("expense", "tibbiyot"),
    ("expense", "ta'lim"),
    ("expense", "kiyim-kechak"),
    ("expense", "gozallik"),
    ("expense", "sport"),
    ("expense", "sayohat"),
    ("expense", "uy-rozg'or"),
    ("expense", "avto"),
    ("expense", "sugirta"),
    ("expense", "kredit-to'lovi"),
    ("expense", "kafe-restoran"),
    ("expense", "onlayn-harid"),
    ("expense", "bolalar-chiqimlari"),
    ("expense", "xayriya"),
    ("expense", "boshqa-xarajat"),
    # ---------- Daromad ----------
    ("income", "maosh"),
    ("income", "oylik-daromad"),
    ("income", "qoshimcha-daromad"),
    ("income", "bonus"),
    ("income", "stipendiya"),
    ("income", "sotish-daromad"),
    ("income", "qarz-qaytarildi"),
    ("income", "boshqa-daromad"),
]


def seed_defaults(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    for ctype, name in DEFAULT_CATEGORIES:
        n = (name or "").strip().lower()
        if not n:
            continue
        if Category.objects.filter(name=n, user__isnull=True).exists():
            continue
        Category.objects.create(
            name=n,
            type=ctype,
            is_default=True,
            user=None,
            monthly_limit=0,
            limit_duration=None,
            limit_set_at=None,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("categories", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed_defaults, noop_reverse),
    ]
