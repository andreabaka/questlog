from django import forms
from .models import Category, Quest, Logger
from django.utils.timezone import now

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g., Reset, Errands, Crafting"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Optional notes…"}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        qs = Category.objects.filter(name__iexact=name)

        # exclude self when editing
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("That category name already exists. Try a different name.")
        return name




class QuestForm(forms.ModelForm):
    class Meta:
        model = Quest
        fields = ["title", "category", "start_date", "end_date", "limited_mobility", "notes"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Quest title"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 6, "placeholder": "Notes…"}),
        }
        error_messages = {
            "title": {"required": "Title is required."},
        }

    def __init__(self, *args, allow_notes_only=False, **kwargs):
        super().__init__(*args, **kwargs)

        # start_date defaults to today (new records)
        if not self.instance or not self.instance.pk:
            self.initial.setdefault("start_date", now().date())

        # category dropdown sorted
        self.fields["category"].queryset = Category.objects.order_by("name")
        self.fields["category"].required = False
        self.fields["limited_mobility"].label = "Limited mobility"

        # If quest is ended and we're in "notes-only" mode, lock everything except notes
        if allow_notes_only:
            for name, field in self.fields.items():
                if name != "notes":
                    field.disabled = True  # visible disabled fields

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")

        # end_date blank = active (allowed)
        if start and end and end < start:
            self.add_error("end_date", "End date can’t be before start date.")

        # Strip title whitespace and keep error friendly
        title = (cleaned.get("title") or "").strip()
        if not title:
            self.add_error("title", "Title is required.")
        else:
            cleaned["title"] = title

        return cleaned

class LoggerForm(forms.ModelForm):
    class Meta:
        model = Logger
        fields = ["completed", "payout", "notes"]
        widgets = {
            "completed": forms.CheckboxInput(attrs={"style": "transform: scale(1.4); margin-right: 0.5rem;"}),
            "payout": forms.NumberInput(attrs={
                "id": "id_payout",
                "inputmode": "numeric",
                "step": "1",
                "placeholder": "e.g., 7",
            }),
            "notes": forms.Textarea(attrs={"rows": 6, "placeholder": "Notes…"}),
        }
        
    def clean_payout(self):
        payout = self.cleaned_data.get("payout")
        if payout in (None, ""):
            return None
        try:
            return int(payout)
        except (TypeError, ValueError):
            raise forms.ValidationError("Payout must be an integer.")
        
        