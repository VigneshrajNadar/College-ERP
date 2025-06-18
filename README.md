# College ERP System

A comprehensive Enterprise Resource Planning (ERP) system designed for educational institutions to manage various academic and administrative processes.

## Features

### Student Management
- Student registration and profile management
- Course enrollment
- Attendance tracking
- Grade management
- Hall ticket generation
- Result viewing
- Revaluation application system

### Staff Management
- Staff registration and profile management
- Course allocation
- Attendance management
- Result entry and management
- KT (Keep Term) application processing
- Revaluation application processing

### HOD (Head of Department) Features
- Department management
- Staff oversight
- Course management
- Exam management
- Hall ticket management
- Result verification

### Admin Features
- User management
- Department management
- Course management
- System configuration
- Reports generation

## Technology Stack

- **Backend**: Django (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite
- **UI Framework**: AdminLTE
- **Authentication**: Django Authentication System

## Installation

1. Clone the repository:
```bash
git clone https://github.com/VigneshrajNadar/College-ERP.git
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Project Structure

```
College-ERP/
├── college_management_system/    # Main project settings
├── main_app/                     # Main application
│   ├── templates/               # HTML templates
│   ├── static/                  # Static files (CSS, JS, images)
│   ├── models.py               # Database models
│   ├── views.py                # View logic
│   └── urls.py                 # URL routing
├── media/                       # User-uploaded files
├── static/                      # Static files
└── requirements.txt            # Project dependencies
```

## Usage

1. Access the admin panel at `/admin` to manage the system
2. Different user roles (Admin, HOD, Staff, Student) have different access levels
3. Follow the on-screen instructions for specific operations

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Contact

Vigneshraj Nadar - [vigneshrajnadar@gmail.com](mailto:vigneshrajnadar@gmail.com)

Project Link: [https://github.com/VigneshrajNadar/College-ERP](https://github.com/VigneshrajNadar/College-ERP)
