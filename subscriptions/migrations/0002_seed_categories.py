from django.db import migrations


CATEGORIES = [
    ("Видео и кино", "video", "play", "#EF6B7A", 1),
    ("Музыка", "music", "music", "#56C9A7", 2),
    ("Программы", "software", "code", "#8B7CFF", 3),
    ("Облако и хранение", "cloud", "cloud", "#68A9FF", 4),
    ("Игры", "gaming", "gamepad", "#D58CF0", 5),
    ("Обучение", "education", "book", "#F0B86B", 6),
    ("Спорт и здоровье", "fitness", "activity", "#72C6C1", 7),
    ("Другое", "other", "layers", "#9299AE", 8),
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("subscriptions", "SubscriptionCategory")
    for name, slug, icon, color, order in CATEGORIES:
        Category.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "icon": icon, "color": color, "sort_order": order},
        )


def remove_categories(apps, schema_editor):
    Category = apps.get_model("subscriptions", "SubscriptionCategory")
    Category.objects.filter(slug__in=[row[1] for row in CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]
    operations = [migrations.RunPython(seed_categories, remove_categories)]
