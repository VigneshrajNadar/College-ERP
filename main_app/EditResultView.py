from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from django.contrib import messages
from .models import Subject, Staff, Student, StudentResult
from .forms import EditResultForm
from django.urls import reverse


class EditResultView(View):
    def get(self, request, *args, **kwargs):
        resultForm = EditResultForm()
        staff = get_object_or_404(Staff, admin=request.user)
        resultForm.fields['subject'].queryset = Subject.objects.filter(staff=staff)
        context = {
            'form': resultForm,
            'page_title': "Edit Student's Result"
        }
        return render(request, "main_app/staff/edit_student_result.html", context)

    def post(self, request, *args, **kwargs):
        form = EditResultForm(request.POST)
        context = {'form': form, 'page_title': "Edit Student's Result"}
        if form.is_valid():
            try:
                student = form.cleaned_data.get('student')
                subject = form.cleaned_data.get('subject')
                semester = form.cleaned_data.get('semester')
                academic_year = form.cleaned_data.get('academic_year')
                internal_marks = float(form.cleaned_data.get('internal_marks', 0))
                external_marks = float(form.cleaned_data.get('external_marks', 0))
                practical_marks = float(form.cleaned_data.get('practical_marks', 0))
                
                # Get or create result
                result, created = StudentResult.objects.get_or_create(
                    student=student,
                    subject=subject,
                    semester=semester,
                    academic_year=academic_year,
                    defaults={
                        'internal_marks': internal_marks,
                        'external_marks': external_marks,
                        'practical_marks': practical_marks
                    }
                )
                
                if not created:
                    result.internal_marks = internal_marks
                    result.external_marks = external_marks
                    result.practical_marks = practical_marks
                    result.save()
                
                messages.success(request, "Result Updated Successfully")
                return redirect(reverse('edit_student_result'))
            except Exception as e:
                messages.error(request, f"Error updating result: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below")
        return render(request, "main_app/staff/edit_student_result.html", context)
