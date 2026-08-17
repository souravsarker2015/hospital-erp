from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.core.permissions import RoleRequiredMixin, TenantMemberRequiredMixin
from apps.core.roles import WARD_ROLES
from apps.users.models import User
from apps.wards.forms import AdmitPatientForm, BedForm, DischargeForm, RoomForm, WardForm
from apps.wards.models import Admission, Bed, Room, Ward
from apps.wards.services import AlreadyDischargedError, BedNotAvailableError, admit_patient, discharge_patient


class WardBoardView(TenantMemberRequiredMixin, TemplateView):
    template_name = "wards/board.html"

    def get_context_data(self, **kwargs):
        wards = Ward.objects.filter(is_active=True).prefetch_related("rooms__beds__admissions")
        ward_id = self.request.GET.get("ward", "")
        if ward_id:
            wards = wards.filter(pk=ward_id)
        return {
            **super().get_context_data(**kwargs),
            "wards": wards,
            "all_wards": Ward.objects.filter(is_active=True),
            "selected_ward": ward_id,
            "can_manage": self.request.user.role in WARD_ROLES,
        }


class WardListView(RoleRequiredMixin, ListView):
    allowed_roles = [User.Role.ADMIN]
    template_name = "wards/ward_list.html"
    context_object_name = "wards_list"

    def get_queryset(self):
        return Ward.objects.filter(is_active=True).prefetch_related("rooms__beds")

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "form": WardForm()}


class WardCreateView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request):
        form = WardForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            if Ward.objects.filter(hospital=request.hospital, name=name).exists():
                form.add_error("name", "A ward with this name already exists.")
            else:
                form.instance.hospital = request.hospital
                form.save()
                return redirect("wards:ward_list")
        wards_list = Ward.objects.filter(is_active=True).prefetch_related("rooms__beds")
        return render(request, "wards/ward_list.html", {"wards_list": wards_list, "form": form})


class WardDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = [User.Role.ADMIN]
    model = Ward
    template_name = "wards/ward_detail.html"
    context_object_name = "ward"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "rooms": self.object.rooms.prefetch_related("beds"),
            "form": RoomForm(),
        }


class RoomCreateView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, ward_pk):
        ward = get_object_or_404(Ward, pk=ward_pk)
        form = RoomForm(request.POST)
        if form.is_valid():
            room_number = form.cleaned_data["room_number"]
            if Room.objects.filter(hospital=request.hospital, ward=ward, room_number=room_number).exists():
                form.add_error("room_number", "This ward already has a room with that number.")
            else:
                form.instance.hospital = request.hospital
                form.instance.ward = ward
                form.save()
                return redirect("wards:ward_detail", pk=ward.pk)
        rooms = ward.rooms.prefetch_related("beds")
        return render(request, "wards/ward_detail.html", {"ward": ward, "rooms": rooms, "form": form})


class RoomDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = [User.Role.ADMIN]
    model = Room
    template_name = "wards/room_detail.html"
    context_object_name = "room"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "beds": self.object.beds.all(), "form": BedForm()}


class BedCreateView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, room_pk):
        room = get_object_or_404(Room, pk=room_pk)
        form = BedForm(request.POST)
        if form.is_valid():
            bed_number = form.cleaned_data["bed_number"]
            if Bed.objects.filter(hospital=request.hospital, room=room, bed_number=bed_number).exists():
                form.add_error("bed_number", "This room already has a bed with that number.")
            else:
                form.instance.hospital = request.hospital
                form.instance.room = room
                form.save()
                return redirect("wards:room_detail", pk=room.pk)
        return render(request, "wards/room_detail.html", {"room": room, "beds": room.beds.all(), "form": form})


class ToggleMaintenanceView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk):
        bed = get_object_or_404(Bed, pk=pk)
        if bed.status == Bed.Status.AVAILABLE:
            bed.status = Bed.Status.MAINTENANCE
            bed.save(update_fields=["status", "updated_at"])
        elif bed.status == Bed.Status.MAINTENANCE:
            bed.status = Bed.Status.AVAILABLE
            bed.save(update_fields=["status", "updated_at"])
        return redirect("wards:room_detail", pk=bed.room_id)


class AdmitPatientView(RoleRequiredMixin, FormView):
    allowed_roles = WARD_ROLES
    form_class = AdmitPatientForm
    template_name = "wards/admit.html"

    def dispatch(self, request, *args, **kwargs):
        self.bed = get_object_or_404(Bed, pk=kwargs["bed_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.bed.status != Bed.Status.AVAILABLE:
            return redirect("wards:board")
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "hospital": self.request.hospital}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "bed": self.bed}

    def form_valid(self, form):
        try:
            admission = admit_patient(
                hospital=self.request.hospital,
                patient=form.cleaned_data["patient_id"],
                bed=self.bed,
                admitting_doctor=form.cleaned_data["admitting_doctor"],
                reason=form.cleaned_data["reason"],
                created_by=self.request.user,
            )
        except BedNotAvailableError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return redirect("wards:admission_detail", pk=admission.pk)


class AdmissionDetailView(RoleRequiredMixin, View):
    allowed_roles = WARD_ROLES

    def get(self, request, pk):
        admission = get_object_or_404(Admission, pk=pk)
        return render(request, "wards/admission_detail.html", {"admission": admission, "form": DischargeForm()})

    def post(self, request, pk):
        admission = get_object_or_404(Admission, pk=pk)
        form = DischargeForm(request.POST)
        if form.is_valid():
            try:
                discharge_patient(
                    admission=admission,
                    discharge_summary=form.cleaned_data["discharge_summary"],
                    discharged_by=request.user,
                )
                return redirect("wards:admission_detail", pk=admission.pk)
            except AlreadyDischargedError:
                pass
        return render(request, "wards/admission_detail.html", {"admission": admission, "form": form})
