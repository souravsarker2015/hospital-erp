from apps.users.models import User

# Registration desk: can register/edit patients and book appointments.
FRONT_DESK_ROLES = [User.Role.ADMIN, User.Role.RECEPTIONIST, User.Role.NURSE]

# Can move an appointment through the OPD queue (check-in / start / complete / etc).
QUEUE_MANAGER_ROLES = [*FRONT_DESK_ROLES, User.Role.DOCTOR]

# Can record a patient's vitals ahead of a consultation.
VITALS_ROLES = [User.Role.ADMIN, User.Role.NURSE, User.Role.DOCTOR]

# Can write consultation notes, diagnosis, prescriptions and lab orders.
CLINICAL_ROLES = [User.Role.ADMIN, User.Role.DOCTOR]

# Can manage the drug catalog, receive stock, and dispense against prescriptions.
PHARMACY_ROLES = [User.Role.ADMIN, User.Role.PHARMACIST]

# Can manage the test catalog, collect samples, and enter lab results.
LAB_ROLES = [User.Role.ADMIN, User.Role.LAB_TECHNICIAN]

# Can generate invoices, add line items, and record payments.
BILLING_ROLES = [User.Role.ADMIN, User.Role.ACCOUNTANT, User.Role.RECEPTIONIST]

# Can admit and discharge patients. Ward/room/bed master setup is
# admin-only (see apps.wards.views), a narrower slice of this same list.
WARD_ROLES = [User.Role.ADMIN, User.Role.NURSE, User.Role.DOCTOR]

# Every hospital-side working role — excludes PATIENT, reserved for the
# later patient-portal phase. Used for broad read access (e.g. printing a
# prescription) that isn't sensitive beyond what the viewer's own role
# already implies access to.
ALL_STAFF_ROLES = [
    User.Role.ADMIN,
    User.Role.DOCTOR,
    User.Role.NURSE,
    User.Role.RECEPTIONIST,
    User.Role.PHARMACIST,
    User.Role.LAB_TECHNICIAN,
    User.Role.ACCOUNTANT,
]
