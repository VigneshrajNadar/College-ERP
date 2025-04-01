import json
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
import re

def is_staff(user):
    return user.user_type == '2'

def is_admin(user):
    return user.user_type == '1'

from .EmailBackend import EmailBackend
from .models import Attendance, Session, Subject, ExamHall, Exam, HallTicket, Course, ExamSubject, KTApplication, RevaluationApplication, Notification, StudentResult, Student, ChatBot
from .utils import generate_hall_tickets_for_exam

# Create your views here.


def login_page(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif request.user.user_type == '2':
            return redirect(reverse("staff_home"))
        else:
            return redirect(reverse("student_home"))
    return render(request, 'main_app/login.html')


def doLogin(request, **kwargs):
    if request.method != 'POST':
        return HttpResponse("<h4>Denied</h4>")
    else:
        #Google recaptcha
        captcha_token = request.POST.get('g-recaptcha-response')
        captcha_url = "https://www.google.com/recaptcha/api/siteverify"
        captcha_key = "6LfTGD4qAAAAALtlli02bIM2MGi_V0cUYrmzGEGd"
        data = {
            'secret': captcha_key,
            'response': captcha_token
        }
        # Make request
        try:
            captcha_server = requests.post(url=captcha_url, data=data)
            response = json.loads(captcha_server.text)
            if response['success'] == False:
                messages.error(request, 'Invalid Captcha. Try Again')
                return redirect('/')
        except:
            messages.error(request, 'Captcha could not be verified. Try Again')
            return redirect('/')
        
        #Authenticate
        user = EmailBackend.authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
        if user != None:
            login(request, user)
            if user.user_type == '1':
                return redirect(reverse("admin_home"))
            elif user.user_type == '2':
                return redirect(reverse("staff_home"))
            else:
                return redirect(reverse("student_home"))
        else:
            messages.error(request, "Invalid details")
            return redirect("/")



def logout_user(request):
    if request.user != None:
        logout(request)
    return redirect("/")


@csrf_exempt
def get_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = Attendance.objects.filter(subject=subject, session=session)
        attendance_list = []
        for attd in attendance:
            data = {
                    "id": attd.id,
                    "attendance_date": str(attd.date),
                    "session": attd.session.id
                    }
            attendance_list.append(data)
        return JsonResponse(json.dumps(attendance_list), safe=False)
    except Exception as e:
        return None


def showFirebaseJS(request):
    data = """
    // Give the service worker access to Firebase Messaging.
// Note that you can only use Firebase Messaging here, other Firebase libraries
// are not available in the service worker.
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-messaging.js');

// Initialize the Firebase app in the service worker by passing in
// your app's Firebase config object.
// https://firebase.google.com/docs/web/setup#config-object
firebase.initializeApp({
    apiKey: "AIzaSyBarDWWHTfTMSrtc5Lj3Cdw5dEvjAkFwtM",
    authDomain: "sms-with-django.firebaseapp.com",
    databaseURL: "https://sms-with-django.firebaseio.com",
    projectId: "sms-with-django",
    storageBucket: "sms-with-django.appspot.com",
    messagingSenderId: "945324593139",
    appId: "1:945324593139:web:03fa99a8854bbd38420c86",
    measurementId: "G-2F2RXTL9GT"
});

// Retrieve an instance of Firebase Messaging so that it can handle background
// messages.
const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function (payload) {
    const notification = JSON.parse(payload);
    const notificationOption = {
        body: notification.body,
        icon: notification.icon
    }
    return self.registration.showNotification(payload.notification.title, notificationOption);
});
    """
    return HttpResponse(data, content_type='application/javascript')

def manage_exam_halls(request):
    """View for managing exam halls"""
    if request.user.user_type != '1':  # Only HOD can access
        return redirect('login_page')
    
    halls = ExamHall.objects.all()
    context = {
        'halls': halls
    }
    return render(request, 'main_app/hod/manage_exam_halls.html', context)

def add_exam_hall(request):
    """View for adding new exam hall"""
    if request.user.user_type != '1':  # Only HOD can access
        return redirect('login_page')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        capacity = request.POST.get('capacity')
        rows = request.POST.get('rows')
        columns = request.POST.get('columns')
        
        ExamHall.objects.create(
            name=name,
            capacity=capacity,
            rows=rows,
            columns=columns
        )
        messages.success(request, 'Exam hall added successfully')
        return redirect('manage_exam_halls')
    
    return render(request, 'main_app/hod/add_exam_hall.html')

def manage_exams(request):
    """View for managing exams"""
    if request.user.user_type != '1':  # Only HOD can access
        return redirect('login_page')
    
    exams = Exam.objects.all()
    context = {
        'exams': exams
    }
    return render(request, 'main_app/hod/manage_exams.html', context)

@login_required
def add_exam(request):
    if request.user.user_type != '1':
        return redirect(reverse('admin_home'))
    
    if request.method == 'POST':
        exam_name = request.POST.get('name')
        course_id = request.POST.get('course')
        hall_id = request.POST.get('hall')
        
        # Get arrays of subjects and their schedules
        subject_ids = request.POST.getlist('subjects[]')
        dates = request.POST.getlist('dates[]')
        start_times = request.POST.getlist('start_times[]')
        end_times = request.POST.getlist('end_times[]')
        
        try:
            course = Course.objects.get(id=course_id)
            hall = ExamHall.objects.get(id=hall_id)
            
            # Create the exam
            exam = Exam.objects.create(
                name=exam_name,
                course=course,
                hall=hall
            )
            
            # Create ExamSubject entries for each subject with its schedule
            for i in range(len(subject_ids)):
                subject = Subject.objects.get(id=subject_ids[i])
                ExamSubject.objects.create(
                    exam=exam,
                    subject=subject,
                    date=dates[i],
                    start_time=start_times[i],
                    end_time=end_times[i]
                )
            
            messages.success(request, 'Exam added successfully!')
            return redirect('manage_exams')
            
        except Exception as e:
            messages.error(request, f'Error adding exam: {str(e)}')
            return redirect('add_exam')
    
    context = {
        'page_title': 'Add Exam',
        'courses': Course.objects.all(),
        'subjects': Subject.objects.all(),
        'halls': ExamHall.objects.all(),
        'today': datetime.now().date()
    }
    return render(request, 'main_app/hod/add_exam.html', context)

def generate_hall_tickets(request, exam_id):
    """View for generating hall tickets for an exam"""
    if request.user.user_type != '1':  # Only HOD can access
        return redirect('login_page')
    
    try:
        tickets = generate_hall_tickets_for_exam(exam_id)
        messages.success(request, f'Successfully generated {len(tickets)} hall tickets')
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('manage_exams')

def view_hall_tickets(request, exam_id):
    """View for viewing hall tickets of an exam"""
    if request.user.user_type != '1':  # Only HOD can access
        return redirect('login_page')
    
    exam = get_object_or_404(Exam, id=exam_id)
    tickets = HallTicket.objects.filter(exam=exam)
    context = {
        'exam': exam,
        'tickets': tickets
    }
    return render(request, 'main_app/hod/view_hall_tickets.html', context)

def student_hall_ticket(request):
    """View for students to view their hall ticket"""
    if request.user.user_type != '3':  # Only students can access
        return redirect('login_page')
    
    student = request.user.student
    tickets = HallTicket.objects.filter(student=student)
    context = {
        'tickets': tickets
    }
    return render(request, 'main_app/student/hall_ticket.html', context)

@login_required(login_url='login')
def student_apply_kt(request):
    student = get_object_or_404(Student, admin=request.user)
    
    # Get all subjects for the student's course
    subjects = Subject.objects.filter(course=student.course_id)
    
    # Get failed subjects (where grade is 'F')
    failed_subjects = []
    for subject in subjects:
        result = StudentResult.objects.filter(
            student=student,
            subject=subject
        ).first()
        if result and result.grade == 'F':
            failed_subjects.append(subject)
    
    # Get existing KT applications
    existing_applications = KTApplication.objects.filter(student=student)
    
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Check if application already exists
        if KTApplication.objects.filter(student=student, subject=subject).exists():
            messages.error(request, f"You have already applied for KT in {subject.name}")
            return redirect('student_apply_kt')
        
        # Create new application
        KTApplication.objects.create(
            student=student,
            subject=subject,
            status='pending'
        )
        messages.success(request, f"Successfully applied for KT in {subject.name}")
        return redirect('student_kt_applications')
    
    context = {
        'student': student,
        'subjects': subjects,
        'failed_subjects': failed_subjects,
        'existing_applications': existing_applications,
        'page_title': 'Apply for KT'
    }
    return render(request, 'student_template/apply_kt.html', context)

@login_required
def student_kt_applications(request):
    if request.user.user_type != '3':
        return redirect('login_page')
    
    student = request.user.student
    applications = KTApplication.objects.filter(student=student).order_by('-created_at')
    context = {
        'applications': applications,
        'page_title': 'My KT Applications'
    }
    return render(request, 'main_app/student/kt_applications.html', context)

@login_required(login_url='login')
def student_apply_revaluation(request):
    student = get_object_or_404(Student, admin=request.user)
    
    # Get all subjects for the student's course
    subjects = Subject.objects.filter(course=student.course_id)
    
    # Get subjects eligible for revaluation (where grade is 'D')
    revaluation_subjects = []
    for subject in subjects:
        result = StudentResult.objects.filter(
            student=student,
            subject=subject
        ).first()
        if result and result.grade == 'D':
            revaluation_subjects.append(subject)
    
    # Get existing revaluation applications
    existing_applications = RevaluationApplication.objects.filter(student=student)
    
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Check if application already exists
        if RevaluationApplication.objects.filter(student=student, subject=subject).exists():
            messages.error(request, f"You have already applied for revaluation in {subject.name}")
            return redirect('student_apply_revaluation')
        
        # Get the current result for the subject
        result = StudentResult.objects.get(student=student, subject=subject)
        
        # Create new application
        RevaluationApplication.objects.create(
            student=student,
            subject=subject,
            current_marks=result.total_marks,
            status='pending'
        )
        messages.success(request, f"Successfully applied for revaluation in {subject.name}")
        return redirect('student_revaluation_applications')
    
    context = {
        'student': student,
        'subjects': subjects,
        'revaluation_subjects': revaluation_subjects,
        'existing_applications': existing_applications,
        'page_title': 'Apply for Revaluation'
    }
    return render(request, 'student_template/apply_revaluation.html', context)

@login_required
def student_revaluation_applications(request):
    if request.user.user_type != '3':
        return redirect('login_page')
    
    student = request.user.student
    applications = RevaluationApplication.objects.filter(student=student).order_by('-created_at')
    context = {
        'applications': applications,
        'page_title': 'My Revaluation Applications'
    }
    return render(request, 'main_app/student/revaluation_applications.html', context)

@login_required(login_url='login')
@user_passes_test(is_staff)
def staff_manage_kt_applications(request):
    kt_applications = KTApplication.objects.all().order_by('-created_at')
    return render(request, 'main_app/staff/manage_kt_applications.html', {
        'kt_applications': kt_applications
    })

@login_required(login_url='login')
@user_passes_test(is_staff)
def staff_manage_revaluation_applications(request):
    revaluation_applications = RevaluationApplication.objects.all().order_by('-created_at')
    return render(request, 'main_app/staff/manage_revaluation_applications.html', {
        'revaluation_applications': revaluation_applications
    })

@login_required(login_url='login')
@user_passes_test(is_staff)
def staff_update_kt_status(request, application_id):
    if request.method == 'POST':
        application = get_object_or_404(KTApplication, id=application_id)
        status = request.POST.get('status')
        remarks = request.POST.get('remarks')
        
        application.status = status
        application.remarks = remarks
        application.save()
        
        # Create notification for student
        Notification.objects.create(
            user=application.student.user,
            title='KT Application Update',
            message=f'Your KT application for {application.subject.name} has been {status}. Remarks: {remarks}',
            notification_type='kt'
        )
        
        messages.success(request, 'KT application status updated successfully.')
    return redirect('staff_manage_kt_applications')

@login_required(login_url='login')
@user_passes_test(is_staff)
def staff_update_revaluation_status(request, application_id):
    if request.method == 'POST':
        application = get_object_or_404(RevaluationApplication, id=application_id)
        status = request.POST.get('status')
        remarks = request.POST.get('remarks')
        
        application.status = status
        application.remarks = remarks
        application.save()
        
        # Create notification for student
        Notification.objects.create(
            user=application.student.user,
            title='Revaluation Application Update',
            message=f'Your revaluation application for {application.subject.name} has been {status}. Remarks: {remarks}',
            notification_type='revaluation'
        )
        
        messages.success(request, 'Revaluation application status updated successfully.')
    return redirect('staff_manage_revaluation_applications')

# Admin views for KT and Revaluation management
@login_required(login_url='login')
@user_passes_test(is_admin)
def admin_manage_kt_applications(request):
    kt_applications = KTApplication.objects.all().order_by('-created_at')
    return render(request, 'main_app/admin/manage_kt_applications.html', {
        'kt_applications': kt_applications
    })

@login_required(login_url='login')
@user_passes_test(is_admin)
def admin_manage_revaluation_applications(request):
    revaluation_applications = RevaluationApplication.objects.all().order_by('-created_at')
    return render(request, 'main_app/admin/manage_revaluation_applications.html', {
        'revaluation_applications': revaluation_applications
    })

@login_required(login_url='login')
@user_passes_test(is_admin)
def admin_update_kt_status(request, application_id):
    if request.method == 'POST':
        application = get_object_or_404(KTApplication, id=application_id)
        status = request.POST.get('status')
        remarks = request.POST.get('remarks')
        
        application.status = status
        application.remarks = remarks
        application.save()
        
        # Create notification for student
        Notification.objects.create(
            user=application.student.user,
            title='KT Application Update',
            message=f'Your KT application for {application.subject.name} has been {status}. Remarks: {remarks}',
            notification_type='kt'
        )
        
        messages.success(request, 'KT application status updated successfully.')
    return redirect('admin_manage_kt_applications')

@login_required(login_url='login')
@user_passes_test(is_admin)
def admin_update_revaluation_status(request, application_id):
    if request.method == 'POST':
        application = get_object_or_404(RevaluationApplication, id=application_id)
        status = request.POST.get('status')
        remarks = request.POST.get('remarks')
        
        application.status = status
        application.remarks = remarks
        application.save()
        
        # Create notification for student
        Notification.objects.create(
            user=application.student.user,
            title='Revaluation Application Update',
            message=f'Your revaluation application for {application.subject.name} has been {status}. Remarks: {remarks}',
            notification_type='revaluation'
        )
        
        messages.success(request, 'Revaluation application status updated successfully.')
    return redirect('admin_manage_revaluation_applications')

@login_required(login_url='login')
def student_notifications(request):
    if request.user.user_type != '3':
        return redirect('login_page')
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    # Mark notifications as read when viewed
    notifications.update(is_read=True)
    
    context = {
        'notifications': notifications,
        'page_title': 'My Notifications'
    }
    return render(request, 'main_app/student/notifications.html', context)

@csrf_exempt
def get_students(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    subject_id = request.POST.get('subject')
    if not subject_id:
        return JsonResponse({'error': 'Subject ID is required'}, status=400)
    
    try:
        subject = Subject.objects.get(id=subject_id)
        # Get students enrolled in the course of the subject
        students = Student.objects.filter(course=subject.course)
        
        student_list = []
        for student in students:
            student_list.append({
                'id': student.id,
                'name': f"{student.admin.first_name} {student.admin.last_name} ({student.admin.username})"
            })
        
        return JsonResponse(json.dumps(student_list), safe=False)
    except Subject.DoesNotExist:
        return JsonResponse({'error': 'Subject not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def chatbot_page(request):
    return render(request, 'main_app/chatbot.html')

def chatbot_query(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip().lower()
            
            # Get all chatbot entries
            all_entries = ChatBot.objects.all()
            
            # Initialize best match variables
            best_match = None
            best_score = 0
            
            # Enhanced keywords for different categories with synonyms
            category_keywords = {
                'academic': [
                    'cgpa', 'attendance', 'kt', 'atkt', 'leave', 'internal', 'grade', 'result',
                    'marks', 'score', 'study', 'exam', 'test', 'assignment', 'project', 'semester',
                    'course', 'subject', 'class', 'lecture', 'teacher', 'professor', 'faculty'
                ],
                'library': [
                    'book', 'library', 'borrow', 'fine', 'return', 'study', 'read', 'textbook',
                    'reference', 'journal', 'magazine', 'research', 'paper', 'publication',
                    'digital', 'online', 'database', 'catalog', 'shelf', 'librarian'
                ],
                'exams': [
                    'exam', 'hall ticket', 'grade', 'result', 'paper', 'question', 'test',
                    'midterm', 'final', 'semester', 'schedule', 'date', 'time', 'venue',
                    'room', 'hall', 'seat', 'admit card', 'marksheet', 'answer sheet'
                ],
                'fees': [
                    'fee', 'payment', 'money', 'pay', 'receipt', 'scholarship', 'tuition',
                    'cost', 'expense', 'charge', 'due', 'installment', 'refund', 'discount',
                    'concession', 'financial', 'bank', 'transaction', 'online payment'
                ],
                'hostel': [
                    'hostel', 'room', 'mess', 'food', 'stay', 'accommodation', 'boarding',
                    'lodging', 'residence', 'dormitory', 'meal', 'dining', 'laundry',
                    'facility', 'amenity', 'furniture', 'maintenance', 'security'
                ],
                'technical': [
                    'portal', 'password', 'login', 'access', 'website', 'app', 'system',
                    'computer', 'internet', 'network', 'email', 'account', 'profile',
                    'settings', 'update', 'download', 'upload', 'file', 'document'
                ],
                'general': [
                    'support', 'help', 'contact', 'profile', 'id card', 'document',
                    'information', 'guide', 'assistance', 'service', 'office', 'department',
                    'staff', 'admin', 'head', 'principal', 'campus', 'facility'
                ]
            }
            
            # Common greetings and farewells
            greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
            farewells = ['bye', 'goodbye', 'see you', 'thank you', 'thanks']
            
            # Check for greetings
            if any(greeting in query for greeting in greetings):
                return JsonResponse({
                    'status': 'success',
                    'answer': "Hello! I'm your college assistant. How can I help you today?",
                    'category': 'general'
                })
            
            # Check for farewells
            if any(farewell in query for farewell in farewells):
                return JsonResponse({
                    'status': 'success',
                    'answer': "Goodbye! Feel free to ask if you need any more help.",
                    'category': 'general'
                })
            
            # Function to calculate similarity score with enhanced matching
            def calculate_similarity(q1, q2):
                # Convert to sets for word matching
                words1 = set(q1.split())
                words2 = set(q2.split())
                
                # Calculate Jaccard similarity
                intersection = len(words1.intersection(words2))
                union = len(words1.union(words2))
                
                if union == 0:
                    return 0
                
                # Add bonus for exact phrase matches
                if q1 in q2 or q2 in q1:
                    return 1.0
                
                # Add bonus for word order similarity
                words1_list = q1.split()
                words2_list = q2.split()
                order_similarity = sum(1 for i in range(min(len(words1_list), len(words2_list)))
                                    if words1_list[i] == words2_list[i]) / max(len(words1_list), len(words2_list))
                
                return (intersection / union) + (order_similarity * 0.2)
            
            # Function to check if query contains category keywords with context
            def get_category_score(query, category):
                score = 0
                words = query.split()
                
                # Check for exact keyword matches
                for keyword in category_keywords.get(category, []):
                    if keyword in query:
                        score += 1
                
                # Check for related words and context
                for word in words:
                    for keyword in category_keywords.get(category, []):
                        if word in keyword or keyword in word:
                            score += 0.5
                
                return score
            
            # Find best match with context
            for entry in all_entries:
                # Calculate similarity with the question
                similarity = calculate_similarity(query, entry.question.lower())
                
                # Add category keyword bonus
                category_score = get_category_score(query, entry.category)
                similarity += (category_score * 0.1)  # Add 10% bonus for each matching keyword
                
                # Add context bonus for related words
                if any(word in query for word in entry.question.lower().split()):
                    similarity += 0.2
                
                # Update best match if this is better
                if similarity > best_score:
                    best_score = similarity
                    best_match = entry
            
            # If we have a good match (similarity > 0.3)
            if best_match and best_score > 0.3:
                response = best_match.answer
                
                # Add related questions based on category and context
                related_questions = ChatBot.objects.filter(
                    category=best_match.category
                ).exclude(id=best_match.id)[:3]
                
                if related_questions:
                    response += "\n\nRelated questions you might want to ask:\n"
                    for q in related_questions:
                        response += f"- {q.question}\n"
                
                # Add follow-up suggestions based on context
                if 'fee' in query or 'payment' in query:
                    response += "\nWould you like to know about:\n- How to pay fees online?\n- Fee structure details?\n- Scholarship opportunities?"
                elif 'exam' in query or 'test' in query:
                    response += "\nWould you like to know about:\n- Exam schedule?\n- Hall ticket download?\n- Result checking?"
                elif 'attendance' in query:
                    response += "\nWould you like to know about:\n- Minimum attendance requirements?\n- Leave application process?\n- Attendance calculation?"
                
                return JsonResponse({
                    'status': 'success',
                    'answer': response,
                    'category': best_match.category
                })
            else:
                # If no good match found, provide a contextual response
                # Try to identify the general topic
                topic_keywords = {
                    'academic': ['study', 'class', 'course', 'subject'],
                    'administrative': ['form', 'application', 'document', 'certificate'],
                    'facilities': ['campus', 'building', 'room', 'hall'],
                    'events': ['festival', 'program', 'competition', 'activity']
                }
                
                identified_topic = None
                for topic, keywords in topic_keywords.items():
                    if any(keyword in query for keyword in keywords):
                        identified_topic = topic
                        break
                
                if identified_topic:
                    response = f"I understand you're asking about {identified_topic} related matters. "
                else:
                    response = "I'm not sure about that. "
                
                response += "Here are some common questions you can ask:\n\n" + \
                           "1. How do I check my attendance?\n" + \
                           "2. What is the fee structure?\n" + \
                           "3. How do I apply for leave?\n" + \
                           "4. What are the library timings?\n" + \
                           "5. How do I get my hall ticket?\n\n" + \
                           "Try asking any of these questions or rephrase your question."
                
                return JsonResponse({
                    'status': 'success',
                    'answer': response,
                    'category': 'general'
                })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

