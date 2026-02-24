from hr.models import Employee
from django.contrib.auth import get_user_model

User = get_user_model()

user = User.objects.get(username='superadmin')
print(f"User ID: {user.id}")

try:
    emp = user.employee_profile
    print(f"Employee ID: {emp.employee_id}")
    print(f"Name: {emp.full_name}")
    print("SUCCESS: Employee portal should work now!")
except:
    print("ERROR: No employee profile found")
