from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Habit, Category, UserProfile, HabitLog


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'Enter your email'
    }))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'First name'
    }))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Last name'
    }))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Create password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})


class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ['name', 'description', 'category', 'frequency', 'priority',
                  'difficulty', 'target_days', 'reminder_time', 'color', 'icon', 'xp_reward']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Morning Run'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                 'placeholder': 'Describe your habit...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'target_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 365}),
            'reminder_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'icon': forms.Select(attrs={'class': 'form-select'}),
            'xp_reward': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100}),
        }

    ICON_CHOICES = [
        ('bi-check-circle', '✓ General'), ('bi-heart-pulse', '❤ Health'),
        ('bi-book', '📖 Learning'), ('bi-lightning', '⚡ Fitness'),
        ('bi-piggy-bank', '🐷 Finance'), ('bi-emoji-smile', '😊 Mindfulness'),
        ('bi-cup-hot', '☕ Morning Routine'), ('bi-moon-stars', '🌙 Night Routine'),
        ('bi-bicycle', '🚲 Exercise'), ('bi-water', '💧 Hydration'),
    ]

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(user=user)
        self.fields['category'].empty_label = "No Category"
        self.fields['icon'].widget = forms.Select(
            choices=self.ICON_CHOICES,
            attrs={'class': 'form-select'}
        )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'color', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
            'color': forms.Select(attrs={'class': 'form-select'}),
            'icon': forms.Select(attrs={'class': 'form-select'}),
        }


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                         'placeholder': 'Tell us about yourself...'}),
        }


class HabitLogNoteForm(forms.ModelForm):
    class Meta:
        model = HabitLog
        fields = ['note', 'mood']
        widgets = {
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                          'placeholder': 'Add a note for today...'}),
            'mood': forms.Select(
                choices=[(1, '😞 Very Bad'), (2, '😕 Bad'), (3, '😐 Okay'), (4, '😊 Good'), (5, '😄 Excellent')],
                attrs={'class': 'form-select'}
            ),
        }
