$(document).ready(function() {
    
    const token = localStorage.getItem('eventer_token');
    const profileModal = new bootstrap.Modal(document.getElementById('profileModal'));
    const editEventModal = new bootstrap.Modal(document.getElementById('editEventModal'));

    function initProfile() {
        $.ajax({
            url: '/users/me',
            method: 'GET',
            xhrFields: { withCredentials: true },
            headers: token ? { "Authorization": "Bearer " + token } : {},
            
            success: function(me) {
                const urlParams = new URLSearchParams(window.location.search);
                const targetId = urlParams.get('id');

                const isMyProfile = !targetId || targetId === me.id;

                if (isMyProfile) {
                    renderProfileData(me, true); 
                } else {
                    fetchPublicProfile(targetId);
                }
            },
            
            error: function(xhr) {
                if(xhr.status === 401 || xhr.status === 403) {
                    window.location.replace('/auth.html');
                } else {
                    console.error("Błąd sesji:", xhr);
                }
            }
        });
    }

    function fetchPublicProfile(userId) {
        $.ajax({
            url: `/users/public/${userId}`,
            method: 'GET',
            headers: token ? { "Authorization": "Bearer " + token } : {},
            success: function(publicUser) {
                renderProfileData(publicUser, false);
            },
            error: function() {
                $('#profilePageName').text("Nie znaleziono użytkownika");
                $('#eventsContainer').html('<div class="alert alert-warning">Nie udało się załadować profilu.</div>');
            }
        });
    }

    function renderProfileData(user, isOwner) {
        $('#profilePageName').text(`${user.first_name} ${user.last_name}`);
        $('#profilePageUsername').text(user.username);
        $('#profilePageDob').text(user.date_of_birth || 'Brak daty');
        
        const bioHtml = user.bio ? escapeHtml(user.bio) : '<span class="text-muted fst-italic">Użytkownik nie napisał jeszcze nic o sobie.</span>';
        $('#profilePageBio').html(bioHtml);

        let genderText = 'Nie podano';
        if(user.gender === 'M') { genderText = 'Mężczyzna'; }
        else if(user.gender === 'F') { genderText = 'Kobieta'; }
        $('#profilePageGender').text(genderText);

        const avatarUrl = `https://ui-avatars.com/api/?name=${user.first_name}+${user.last_name}&background=343a40&color=fff&size=256`;
        $('#profilePageAvatar').attr('src', avatarUrl);

        if (isOwner) {
            $('#editProfileBtn').removeClass('d-none').data('user', user);
            document.title = "Twój Profil - Eventer";
        } else {
            $('#editProfileBtn').addClass('d-none');
            document.title = `${user.first_name} ${user.last_name} - Eventer`;
        }

        loadUserEvents(user.id, isOwner);
    }

    function loadUserEvents(userId, isOwner) {
        const $container = $('#eventsContainer');
        const endpoint = isOwner ? '/events/me' : `/events/user/${userId}`;

        $.ajax({
            url: endpoint,
            method: 'GET',
            xhrFields: { withCredentials: true },
            headers: token ? { "Authorization": "Bearer " + token } : {},
            success: function(events) {
                $('#userEventsCount').text(events.length);
                $container.empty();

                if (events.length === 0) {
                    const msg = isOwner ? "Nie dodałeś jeszcze żadnych wydarzeń." : "Ten użytkownik nie dodał jeszcze żadnych wydarzeń.";
                    $container.html(`
                        <div class="text-center py-5 text-muted">
                            <i class="far fa-folder-open fa-3x mb-3 opacity-50"></i>
                            <p>${msg}</p>
                            ${isOwner ? '<a href="/add-event.html" class="btn btn-sm btn-outline-dark rounded-pill">Dodaj pierwsze</a>' : ''}
                        </div>
                    `);
                    return;
                }

                events.forEach(event => {
                    const dateObj = new Date(event.event_date);
                    const dateStr = dateObj.toLocaleDateString('pl-PL', { 
                        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute:'2-digit' 
                    });
                    const imgUrl = `https://picsum.photos/seed/${event.id}/800/300`;

                    let buttonsHtml = '';
                    if (isOwner) {
                        const eventData = encodeURIComponent(JSON.stringify(event));

                        buttonsHtml = `
                        <div class="d-flex justify-content-end gap-2 mt-3">
                            <button class="btn btn-sm btn-outline-dark edit-event-btn" data-event="${eventData}">
                                <i class="fas fa-edit me-1"></i> Edytuj
                            </button>
                            <button class="btn btn-sm btn-outline-danger delete-event-btn" data-id="${event.id}">
                                <i class="fas fa-trash me-1"></i> Usuń
                            </button>
                        </div>`;
                    }

                    const card = `
                        <div class="card border-0 shadow-sm rounded-4 mb-4 overflow-hidden">
                            <div style="height: 180px; background-image: url('${imgUrl}'); background-size: cover; background-position: center;">
                                <div class="w-100 h-100 d-flex align-items-end p-3" style="background: linear-gradient(to top, rgba(0,0,0,0.6), transparent);">
                                    <span class="badge bg-white text-dark rounded-pill shadow-sm">
                                        <i class="fas fa-calendar-alt me-1"></i> ${dateStr}
                                    </span>
                                </div>
                            </div>
                            <div class="card-body p-4">
                                <h5 class="fw-bold mb-1 text-dark">${escapeHtml(event.title)}</h5>
                                <p class="text-muted small mb-0">${escapeHtml(event.description || 'Brak opisu.')}</p>
                                ${buttonsHtml}
                            </div>
                        </div>
                    `;
                    $container.append(card);
                });
            }
        });
    }

    $('#editProfileBtn').click(function() {
        const user = $(this).data('user');
        $('#editFirstName').val(user.first_name);
        $('#editLastName').val(user.last_name);
        $('#editUsername').val(user.username);
        $('#editBio').val(user.bio || "");
        $('#modalAvatar').attr('src', $('#profilePageAvatar').attr('src'));
        $('#profileAlert').addClass('d-none');
        profileModal.show();
    });

    $('#editProfileForm').submit(function(e) {
        e.preventDefault();
        const updateData = {
            first_name: $('#editFirstName').val(),
            last_name: $('#editLastName').val(),
            username: $('#editUsername').val(),
            bio: $('#editBio').val()
        };
        $.ajax({
            url: "/users/me",
            method: "PATCH",
            contentType: "application/json",
            headers: token ? { Authorization: "Bearer " + token } : {},
            data: JSON.stringify(updateData),
            success: function() { 
                profileModal.hide(); 
                initProfile();
            },
            error: function(xhr) { $("#profileAlert").text("Błąd zapisu.").removeClass("d-none"); }
        });
    });

    $(document).on('click', '.edit-event-btn', function() {
        const eventData = JSON.parse(decodeURIComponent($(this).data('event')));
        
        $('#editEventId').val(eventData.id);
        $('#editEventTitleInput').val(eventData.title);
        $('#editEventDescInput').val(eventData.description);
        
        const d = new Date(eventData.event_date);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        const dateStr = d.toISOString().slice(0, 16);
        $('#editEventDateInput').val(dateStr);

        editEventModal.show();
    });

    $('#editEventForm').submit(function(e) {
        e.preventDefault();
        const eventId = $('#editEventId').val();
        const updateData = {
            title: $('#editEventTitleInput').val(),
            description: $('#editEventDescInput').val(),
            event_date: $('#editEventDateInput').val()
        };

        $.ajax({
            url: '/events/' + eventId,
            method: 'PATCH',
            contentType: 'application/json',
            headers: token ? { Authorization: "Bearer " + token } : {},
            data: JSON.stringify(updateData),
            success: function() {
                editEventModal.hide();
                initProfile();
            },
            error: function(xhr) {
                alert("Błąd zapisu: " + (xhr.responseJSON?.detail || "Error"));
            }
        });
    });

    $(document).on('click', '.delete-event-btn', function() {
        if(!confirm("Czy na pewno chcesz usunąć to wydarzenie?")) return;
        const eventId = $(this).data('id');
        $.ajax({
            url: '/events/' + eventId,
            method: 'DELETE',
            headers: token ? { "Authorization": "Bearer " + token } : {},
            success: function() { initProfile(); }
        });
    });

    function escapeHtml(text) {
        if (!text) return "";
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/\n/g, "<br>");
    }

    initProfile();
});