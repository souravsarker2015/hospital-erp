from apps.users.models import User

# Registration desk: can register/edit patients and book appointments.
FRONT_DESK_ROLES = [User.Role.ADMIN, User.Role.RECEPTIONIST, User.Role.NURSE]

# Can move an appointment through the OPD queue (check-in / start / complete / etc).
QUEUE_MANAGER_ROLES = [*FRONT_DESK_ROLES, User.Role.DOCTOR]
