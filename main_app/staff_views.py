import json

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import tempfile
from datetime import date, datetime
from xhtml2pdf import pisa
from io import BytesIO

# Try importing xhtml2pdf, but don't fail if it's not available
try:
    from xhtml2pdf import pisa
    PDF_GENERATION_AVAILABLE = True
except ImportError:
    PDF_GENERATION_AVAILABLE = False

from .forms import *
from .models import *
from . import forms, models

def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    total_students = Student.objects.filter(course=staff.course).count()
    total_leave = LeaveReportStaff.objects.filter(staff=staff).count()
    subjects = Subject.objects.filter(staff=staff)
    total_subject = subjects.count()
    attendance_list = Attendance.objects.filter(subject__in=subjects)
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name)
        attendance_list.append(attendance_count)
    context = {
        'page_title': 'Staff Panel - ' + str(staff.admin.first_name) + ' ' + str(staff.admin.last_name[0]) + '' + ' (' + str(staff.course) + ')',
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list
    }
    return render(request, 'staff_template/home_content.html', context)


def staff_take_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Take Attendance'
    }

    return render(request, 'staff_template/staff_take_attendance.html', context)


@csrf_exempt
def get_students(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        
        # If session_id is provided, use it for attendance
        if session_id:
            session = get_object_or_404(Session, id=session_id)
            students = Student.objects.filter(course_id=subject.course.id, session=session)
        else:
            # For result entry, get all students in the course
            students = Student.objects.filter(course_id=subject.course.id)
        
        student_data = []
        for student in students:
            data = {
                "id": student.id,
                "name": f"{student.admin.first_name} {student.admin.last_name} ({student.admin.email})"
            }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def save_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    students = json.loads(student_data)
    try:
        session = get_object_or_404(Session, id=session_id)
        subject = get_object_or_404(Subject, id=subject_id)
        attendance = Attendance(session=session, subject=subject, date=date)
        attendance.save()

        for student_dict in students:
            student = get_object_or_404(Student, id=student_dict.get('id'))
            attendance_report = AttendanceReport(student=student, attendance=attendance, status=student_dict.get('status'))
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_update_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Update Attendance'
    }

    return render(request, 'staff_template/staff_update_attendance.html', context)


@csrf_exempt
def get_student_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        date = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_data = AttendanceReport.objects.filter(attendance=date)
        student_data = []
        for attendance in attendance_data:
            data = {"id": attendance.student.admin.id,
                    "name": attendance.student.admin.last_name + " " + attendance.student.admin.first_name,
                    "status": attendance.status}
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e


@csrf_exempt
def update_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    students = json.loads(student_data)
    try:
        attendance = get_object_or_404(Attendance, id=date)

        for student_dict in students:
            student = get_object_or_404(
                Student, admin_id=student_dict.get('id'))
            attendance_report = get_object_or_404(AttendanceReport, student=student, attendance=attendance)
            attendance_report.status = student_dict.get('status')
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_apply_leave(request):
    form = LeaveReportStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStaff.objects.filter(staff=staff),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('staff_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_apply_leave.html", context)


def staff_feedback(request):
    form = FeedbackStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStaff.objects.filter(staff=staff),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('staff_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_feedback.html", context)


def staff_view_profile(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = StaffEditForm(request.POST or None, request.FILES or None,instance=staff)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = staff.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                staff.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('staff_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "staff_template/staff_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "staff_template/staff_view_profile.html", context)

    return render(request, "staff_template/staff_view_profile.html", context)


@csrf_exempt
def staff_fcmtoken(request):
    token = request.POST.get('token')
    try:
        staff_user = get_object_or_404(CustomUser, id=request.user.id)
        staff_user.fcm_token = token
        staff_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def staff_view_notification(request):
    staff = get_object_or_404(Staff, admin=request.user)
    notifications = NotificationStaff.objects.filter(staff=staff)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "staff_template/staff_view_notification.html", context)


def staff_add_result(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff=staff)
    context = {
        'page_title': 'Result Upload',
        'subjects': subjects
    }
    
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student')
            subject_id = request.POST.get('subject')
            semester = request.POST.get('semester')
            academic_year = request.POST.get('academic_year')
            internal_marks = float(request.POST.get('internal_marks', 0))
            external_marks = float(request.POST.get('external_marks', 0))
            practical_marks = float(request.POST.get('practical_marks', 0))
            
            student = get_object_or_404(Student, id=student_id)
            subject = get_object_or_404(Subject, id=subject_id)
            
            # Check if result already exists
            existing_result = StudentResult.objects.filter(
                student=student,
                subject=subject,
                semester=semester,
                academic_year=academic_year
            ).first()
            
            if existing_result:
                messages.error(request, 'Result already exists for this student in this semester')
                return redirect('staff_add_result')
            
            # Create new result
            StudentResult.objects.create(
                student=student,
                subject=subject,
                semester=semester,
                academic_year=academic_year,
                internal_marks=internal_marks,
                external_marks=external_marks,
                practical_marks=practical_marks
            )
            
            messages.success(request, 'Result added successfully')
            return redirect('staff_add_result')
            
        except Exception as e:
            messages.error(request, f'Error adding result: {str(e)}')
            return redirect('staff_add_result')
    
    return render(request, "main_app/staff/add_result.html", context)


@csrf_exempt
def fetch_student_result(request):
    try:
        subject_id = request.POST.get('subject')
        student_id = request.POST.get('student')
        
        if not subject_id or not student_id:
            return JsonResponse({'error': 'Subject and student are required'}, status=400)
            
        subject = get_object_or_404(Subject, id=subject_id)
        student = get_object_or_404(Student, id=student_id)
        
        # Get the latest result for this student and subject
        result = StudentResult.objects.filter(
            student=student,
            subject=subject
        ).order_by('-academic_year', '-semester').first()
        
        if result:
            return JsonResponse({
                'internal_marks': float(result.internal_marks),
                'external_marks': float(result.external_marks),
                'practical_marks': float(result.practical_marks),
                'semester': result.semester,
                'academic_year': result.academic_year
            })
        else:
            return JsonResponse({
                'internal_marks': 0,
                'external_marks': 0,
                'practical_marks': 0,
                'semester': '',
                'academic_year': ''
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

#library
def add_book(request):
    if request.method == "POST":
        name = request.POST['name']
        author = request.POST['author']
        isbn = request.POST['isbn']
        category = request.POST['category']


        books = Book.objects.create(name=name, author=author, isbn=isbn, category=category )
        books.save()
        alert = True
        return render(request, "staff_template/add_book.html", {'alert':alert})
    context = {
        'page_title': "Add Book"
    }
    return render(request, "staff_template/add_book.html",context)

#issue book


def issue_book(request):
    form = forms.IssueBookForm()
    if request.method == "POST":
        form = forms.IssueBookForm(request.POST)
        if form.is_valid():
            obj = models.IssuedBook()
            obj.student_id = request.POST['name2']
            obj.isbn = request.POST['isbn2']
            obj.save()
            alert = True
            return render(request, "staff_template/issue_book.html", {'obj':obj, 'alert':alert})
    return render(request, "staff_template/issue_book.html", {'form':form})

def view_issued_book(request):
    issuedBooks = IssuedBook.objects.all()
    details = []
    for i in issuedBooks:
        days = (date.today()-i.issued_date)
        d=days.days
        fine=0
        if d>14:
            day=d-14
            fine=day*5
        books = list(models.Book.objects.filter(isbn=i.isbn))
        # students = list(models.Student.objects.filter(admin=i.admin))
        i=0
        for l in books:
            t=(books[i].name,books[i].isbn,issuedBooks[0].issued_date,issuedBooks[0].expiry_date,fine)
            i=i+1
            details.append(t)
    return render(request, "staff_template/view_issued_book.html", {'issuedBooks':issuedBooks, 'details':details})

def generate_result(request):
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        semester = request.POST.get('semester')
        academic_year = request.POST.get('academic_year')
        
        subject = get_object_or_404(Subject, id=subject_id)
        staff = get_object_or_404(Staff, admin=request.user)
        
        if subject.staff != staff:
            messages.error(request, "You don't have permission to generate results for this subject")
            return redirect('staff_home')
            
        results = StudentResult.objects.filter(
            subject=subject,
            semester=semester,
            academic_year=academic_year
        ).order_by('student__admin__email')
        
        context = {
            'subject': subject,
            'semester': semester,
            'academic_year': academic_year,
            'results': results,
            'today': datetime.now(),
            'page_title': f"Result Sheet - {subject.name}"
        }
        
        return render(request, 'main_app/staff/result_sheet.html', context)
    else:
        staff = get_object_or_404(Staff, admin=request.user)
        subjects = Subject.objects.filter(staff=staff)
        context = {
            'subjects': subjects,
            'page_title': 'Generate Result'
        }
        return render(request, 'main_app/staff/generate_result.html', context)

def download_result(request, subject_id, semester, academic_year):
    subject = get_object_or_404(Subject, id=subject_id)
    staff = get_object_or_404(Staff, admin=request.user)
    
    if subject.staff != staff:
        messages.error(request, "You don't have permission to download results for this subject")
        return redirect('staff_home')
        
    results = StudentResult.objects.filter(
        subject=subject,
        semester=semester,
        academic_year=academic_year
    ).order_by('student__admin__email')
    
    context = {
        'subject': subject,
        'semester': semester,
        'academic_year': academic_year,
        'results': results,
        'today': datetime.now(),
        'page_title': f"Result Sheet - {subject.name}"
    }
    
    if not PDF_GENERATION_AVAILABLE:
        messages.error(request, "PDF generation is not available. Please install xhtml2pdf.")
        return redirect('staff_generate_result')
    
    try:
        html_string = render_to_string('staff_template/result_sheet.html', context)
        
        # Create a BytesIO object to receive the PDF data
        buffer = BytesIO()
        
        # Create the PDF object, using the BytesIO object as its "file."
        pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), buffer)
        
        # Get the value of the BytesIO buffer and write it to the response
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="result_sheet_{subject.name}_{semester}_{academic_year}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('staff_generate_result')