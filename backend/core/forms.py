from django import forms
from .models import Project, ProjectMedia


class ProjectForm(forms.ModelForm):
    revision = forms.CharField(widget=forms.HiddenInput, required=False)
    class Meta:
        model = Project
        fields = ["title", "slug", "object_type", "location", "task", "solution", "materials", "area", "price", "services", "featured", "position", "editor_notes"]
        labels = {"title": "Название проекта", "slug": "Адрес страницы (латиницей)", "object_type": "Тип объекта", "location": "Локация для публикации", "task": "Задача", "solution": "Решение и результат", "materials": "Материалы", "area": "Площадь, м²", "price": "Стоимость, ₽ (если разрешено)", "services": "Применённые решения", "featured": "Показывать на главной", "position": "Порядок показа", "editor_notes": "Что нужно уточнить (видно только в кабинете)"}
        widgets = {"task": forms.Textarea(attrs={"rows": 4}), "solution": forms.Textarea(attrs={"rows": 6}), "materials": forms.Textarea(attrs={"rows": 3}), "services": forms.CheckboxSelectMultiple()}
        help_texts = {"slug": "Например: penthouse-rumyantseva. После публикации лучше не менять.", "location": "Указывайте точный адрес только с разрешения клиента.", "price": "Оставьте пустым, если стоимость не должна быть опубликована.", "position": "Меньшее число показывается раньше."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["editor_notes"].widget.attrs.update(rows=4, placeholder="Нужно указать: объект, площадь, подтверждение фотографий и разрешение на публикацию адреса.")
        for name, text in {"location": "Нужно указать локацию", "area": "Нужно указать площадь, если известна", "materials": "Нужно указать подтверждённые материалы", "task": "Нужно описать задачу объекта", "solution": "Нужно описать выполненные решения"}.items():
            self.fields[name].widget.attrs["placeholder"] = text
        if self.instance.pk:
            self.fields["revision"].initial = self.instance.updated_at.isoformat()


class MediaForm(forms.ModelForm):
    class Meta:
        model = ProjectMedia
        fields = ["alt", "caption", "section"]
        labels = {"alt": "Описание фотографии", "caption": "Подпись", "section": "Раздел галереи"}
