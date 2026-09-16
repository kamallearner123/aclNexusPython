import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lms.models import LMSUser

User = get_user_model()


class Command(BaseCommand):
    help = "Synchronize real cohort users from core identity directory to LMS profiles without dummy course data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Synchronizing cohort users for LearnHub LMS..."))
        default_pwd = os.environ.get('SEED_DEFAULT_PASSWORD', 'AclMission@123')

        cohort_data = [
            {'id': 2, 'email': 'kamal@aptcomputinglabs.com', 'first': 'Kamal', 'last': 'Mukiri', 'role': 'MANAGER'},
            {'id': 3, 'email': 'admin@admin.com', 'first': 'System', 'last': 'Admin', 'role': 'ADMIN'},
            {'id': 4, 'email': 'kamalbec2004@gmail.com', 'first': 'Kamal', 'last': 'M', 'role': 'USER'},
            {'id': 5, 'email': 'roopa@aptcomputinglabs.com', 'first': 'Roopa', 'last': 'S', 'role': 'USER'},
            {'id': 6, 'email': 'robin@aptcomputinglabs.com', 'first': 'Robin', 'last': 'V', 'role': 'USER'},
            {'id': 7, 'email': 'thanseef@aptcomputinglabs.com', 'first': 'Thanseef', 'last': 'M', 'role': 'USER'},
            {'id': 8, 'email': 'supriya@aptcomputinglabs.com', 'first': 'Supriya', 'last': 'Thoppana', 'role': 'MENTOR'},
            {'id': 9, 'email': 'dhanush@aptcomputinglabs.com', 'first': 'Dhanush', 'last': 'K', 'role': 'USER'},
            {'id': 10, 'email': 'supriyathoppana@gmail.com', 'first': 'Supriya', 'last': 'T', 'role': 'USER'},
            {'id': 11, 'email': 'mageshbj83@gmail.com', 'first': 'Magesh', 'last': 'B', 'role': 'USER'},
            {'id': 12, 'email': 'emamul.embedded@gmail.com', 'first': 'Emamul', 'last': 'H', 'role': 'STUDENT'},
            {'id': 13, 'email': 'sadatul_islama@yahoo.co.in', 'first': 'Sadatul', 'last': 'I', 'role': 'STUDENT'},
            {'id': 14, 'email': 'balugollapothu67@gmail.com', 'first': 'Balu', 'last': 'G', 'role': 'STUDENT'},
            {'id': 15, 'email': 'srk.kolluru@gmail.com', 'first': 'SRK', 'last': 'Kolluru', 'role': 'STUDENT'},
            {'id': 16, 'email': 'hemasundar740@gmail.com', 'first': 'Hemasundar', 'last': 'R', 'role': 'STUDENT'},
            {'id': 17, 'email': 'mdqayyum.se@gmail.com', 'first': 'MD', 'last': 'Qayyum', 'role': 'STUDENT'},
            {'id': 18, 'email': 'lok4979@gmail.com', 'first': 'Lokesh', 'last': 'K', 'role': 'STUDENT'},
        ]

        count = 0
        for item in cohort_data:
            core_user = User.objects.filter(id=item['id']).first()
            if not core_user:
                core_user = User.objects.filter(email=item['email']).first()

            if not core_user:
                core_user = User(
                    id=item['id'],
                    email=item['email'],
                    first_name=item['first'],
                    last_name=item['last'],
                    is_active=True,
                )
                if item['role'] == 'ADMIN':
                    core_user.is_staff = True
                    core_user.is_superuser = True
                core_user.set_password(default_pwd)
                core_user.save()

            # Ensure LMS profile exists and is linked without dummy placeholder text
            LMSUser.objects.update_or_create(
                external_user_id=core_user.id,
                defaults={
                    'email': item['email'],
                    'first_name': core_user.first_name or item['first'],
                    'last_name': core_user.last_name or item['last'],
                    'role': item['role'],
                    'specialization': '',
                    'bio': '',
                    'phone': '',
                    'avatar_url': f"https://ui-avatars.com/api/?name={item['first']}+{item['last']}&background=1e293b&color=38bdf8",
                    'is_active': True,
                }
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully synchronized {count} LMS user profiles."))
