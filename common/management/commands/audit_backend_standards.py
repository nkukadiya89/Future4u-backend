from collections import defaultdict
from pathlib import Path
import re

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Audit backend standards app by app."

    API_DIRS = {"api", "views", "repositories", "selectors", "services"}
    AUDIT_FIELDS = {"created_at", "updated_at", "created_by", "updated_by"}

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        apps = self._installed_project_apps()
        report = defaultdict(list)

        for app in apps:
            app_dir = base_dir / app
            if not app_dir.exists():
                continue

            self._check_all_in_api_paths(app, app_dir, report)
            self._check_silent_exception_handling(app, app_dir, report)
            self._check_pagination_class_usage(app, app_dir, report)
            self._check_model_audit_fields(app, app_dir, report)

        self._print_report(apps, report)

    def _installed_project_apps(self):
        return sorted(
            app
            for app in settings.INSTALLED_APPS
            if "." not in app and (Path(settings.BASE_DIR) / app).exists()
        )

    def _iter_python_files(self, app_dir: Path):
        for py_file in app_dir.rglob("*.py"):
            if any(part in {"migrations", "__pycache__"} for part in py_file.parts):
                continue
            yield py_file

    def _check_all_in_api_paths(self, app: str, app_dir: Path, report):
        for py_file in self._iter_python_files(app_dir):
            parts = set(py_file.parts)
            if not parts.intersection(self.API_DIRS):
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(content.splitlines(), 1):
                if ".all(" in line:
                    report[app].append(f"{py_file.relative_to(app_dir)}:{line_no} uses .all()")

    def _check_silent_exception_handling(self, app: str, app_dir: Path, report):
        pattern = re.compile(r"except\s+Exception\s*:\s*(pass)?")
        for py_file in self._iter_python_files(app_dir):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(content.splitlines(), 1):
                if pattern.search(line.strip()):
                    report[app].append(
                        f"{py_file.relative_to(app_dir)}:{line_no} has broad except"
                    )

    def _check_pagination_class_usage(self, app: str, app_dir: Path, report):
        for py_file in self._iter_python_files(app_dir):
            if py_file.name not in {"views.py"}:
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "ModelViewSet" not in content:
                continue
            if "def list(" in content and "pagination_class =" not in content:
                report[app].append(
                    f"{py_file.relative_to(app_dir)} has list() without pagination_class"
                )

    def _check_model_audit_fields(self, app: str, app_dir: Path, report):
        model_file = app_dir / "models.py"
        if not model_file.exists():
            return
        content = model_file.read_text(encoding="utf-8", errors="ignore")
        if "class " not in content:
            return

        model_classes = re.findall(r"^class\s+(\w+)\(models\.Model\):", content, re.MULTILINE)
        if not model_classes:
            return

        for model_name in model_classes:
            block = self._extract_class_block(content, model_name)
            if "managed = False" in block:
                continue
            if "abstract = True" in block:
                continue
            missing = [
                field
                for field in self.AUDIT_FIELDS
                if re.search(rf"\b{re.escape(field)}\b\s*=", block) is None
            ]
            if missing:
                report[app].append(
                    f"models.py:{model_name} missing audit fields: {', '.join(missing)}"
                )

    def _extract_class_block(self, content: str, class_name: str):
        pattern = re.compile(
            rf"^class\s+{re.escape(class_name)}\(models\.Model\):\n(.*?)(?=^class\s+\w+\(|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(content)
        return match.group(1) if match else ""

    def _print_report(self, apps, report):
        self.stdout.write(self.style.NOTICE("Backend standards audit by app"))
        for app in apps:
            issues = report.get(app, [])
            if not issues:
                self.stdout.write(self.style.SUCCESS(f"- {app}: PASS"))
                continue
            self.stdout.write(self.style.WARNING(f"- {app}: {len(issues)} issue(s)"))
            for issue in issues:
                self.stdout.write(f"  - {issue}")
