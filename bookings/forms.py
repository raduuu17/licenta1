from django import forms
from .models import Booking, Review

class DateInput(forms.DateInput):
    input_type = 'date'
    attrs = {'class': 'form-control'}

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['check_in_date', 'check_out_date', 'guests', 'special_requests']
        widgets = {
            'check_in_date': DateInput(),
            'check_out_date': DateInput(),
            'guests': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get('check_in_date')
        check_out_date = cleaned_data.get('check_out_date')
        
        if check_in_date and check_out_date:
            if check_out_date <= check_in_date:
                self.add_error('check_out_date', "Check-out date must be after check-in date")
        
        return cleaned_data

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[
                (1, '1 ★ - Poor'),
                (2, '2 ★★ - Fair'),
                (3, '3 ★★★ - Good'),
                (4, '4 ★★★★ - Very Good'),
                (5, '5 ★★★★★ - Excellent')
            ], attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Share your experience during your stay...'
            })
        }