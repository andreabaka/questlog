# Questlog

Personal quest + logging app built with Django.

## How to run locally

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install django
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
