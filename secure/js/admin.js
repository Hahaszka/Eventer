$(document).ready(function() {
    const token = localStorage.getItem('eventer_token');
    
    const authHeaders = token ? { "Authorization": "Bearer " + token } : {};
    const xhrConfig = { withCredentials: true };

    function escapeHtml(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // --- 1. ŁADOWANIE DANYCH ---
    function loadUsers() {
        console.log("--> Pobieranie listy użytkowników...");
                
        $.ajax({
            url: '/admin/users',
            method: 'GET',
            headers: authHeaders,
            xhrFields: xhrConfig,
            success: function(response) {

                if (!Array.isArray(response)) {
                    console.error("Błąd: Otrzymano niepoprawne dane", response);
                    alert("Błąd API: Oczekiwano listy użytkowników.");
                    return;
                }

                const $tbody = $('#usersTable tbody').empty();

                response.forEach(u => {
                    const id = u.id;
                    const email = u.email || 'Brak emaila';
                    const firstName = u.first_name || '-';
                    const lastName = u.last_name || '-';
                    const username = u.username || '-';

                    const badges = `
                        ${u.is_superuser ? '<span class="badge bg-danger me-1">ADMIN</span>' : ''}
                        ${u.is_active ? '<span class="badge bg-success">AKTYWNY</span>' : '<span class="badge bg-secondary">ZBANOWANY</span>'}
                        ${u.is_verified ? '<span class="badge text-bg-light border">WERYF.</span>' : ''}
                    `;

                    const safeUserJson = JSON.stringify(u).replace(/'/g, "&apos;").replace(/"/g, "&quot;");

                    const row = `
                        <tr>
                            <td class="ps-4">
                                <div class="fw-bold text-dark">${escapeHtml(email)}</div>
                                <div class="small text-muted" style="font-size: 0.75rem">${id}</div>
                            </td>
                            <td>${escapeHtml(firstName)} ${escapeHtml(lastName)}</td>
                            <td>${escapeHtml(username)}</td>
                            <td>${badges}</td>
                            <td class="text-end pe-4">
                                <button class="btn btn-sm btn-outline-dark action-btn me-1 edit-btn" data-user='${safeUserJson}'>
                                    <i class="fas fa-pen fa-xs"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger action-btn delete-btn" data-id="${id}">
                                    <i class="fas fa-trash fa-xs"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                    $tbody.append(row);
                });
            },
            error: function(xhr) {
                console.error("--> Błąd API:", xhr);
                
                if (xhr.status === 403 || xhr.status === 401) {
                    alert("Sesja wygasła lub brak uprawnień administratora.");
                    window.location.replace('/dashboard.html');
                } else {
                    alert("Wystąpił błąd serwera: " + xhr.status);
                }
            }
        });
    }

    loadUsers();

    // --- 2. TWORZENIE ---
    $('#createForm').submit(function(e) {
        e.preventDefault();
        
        const formData = {
            email: $('[name="email"]').val(),
            password: $('[name="password"]').val(),
            username: $('[name="username"]').val(),
            first_name: $('[name="first_name"]').val(),
            last_name: $('[name="last_name"]').val(),
            date_of_birth: $('[name="date_of_birth"]').val(),
            is_active: true,
            is_superuser: false,
            is_verified: true
        };

        $.ajax({
            url: '/admin/users',
            method: 'POST',
            contentType: 'application/json',
            headers: authHeaders,
            xhrFields: xhrConfig,
            data: JSON.stringify(formData),
            success: function() {
                const modal = bootstrap.Modal.getInstance(document.getElementById('createUserModal'));
                modal.hide();
                $('#createForm')[0].reset();
                loadUsers();
            },
            error: function(xhr) {
                const msg = xhr.responseJSON?.detail || "Nieznany błąd";
                alert("Nie udało się dodać użytkownika: " + msg);
            }
        });
    });

    // --- 3. PRZYGOTOWANIE DO EDYCJI ---
    $(document).on('click', '.edit-btn', function() {
        const userData = $(this).data('user');
        
        $('#editUserId').val(userData.id);
        $('#editFirstName').val(userData.first_name);
        $('#editLastName').val(userData.last_name);
        $('#editUsername').val(userData.username);
        
        $('#editIsActive').prop('checked', userData.is_active);
        $('#editIsSuperuser').prop('checked', userData.is_superuser);
        $('#editIsVerified').prop('checked', userData.is_verified);
        
        const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
        modal.show();
    });

    // --- 4. ZAPISYWANIE ZMIAN ---
    $('#editForm').submit(function(e) {
        e.preventDefault();
        
        const userId = $('#editUserId').val();
        
        const updateData = {
            first_name: $('#editFirstName').val(),
            last_name: $('#editLastName').val(),
            username: $('#editUsername').val(),
            is_active: $('#editIsActive').is(':checked'),
            is_superuser: $('#editIsSuperuser').is(':checked'),
            is_verified: $('#editIsVerified').is(':checked')
        };

        $.ajax({
            url: '/admin/users/' + userId,
            method: 'PATCH',
            contentType: 'application/json',
            headers: authHeaders,
            xhrFields: xhrConfig,
            data: JSON.stringify(updateData),
            success: function() {
                const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
                modal.hide();
                loadUsers();
            },
            error: function(xhr) {
                const msg = xhr.responseJSON?.detail || xhr.responseText;
                alert("Błąd podczas edycji: " + msg);
            }
        });
    });

    // --- 5. USUWANIE ---
    $(document).on('click', '.delete-btn', function() {
        if (!confirm("Czy na pewno chcesz bezpowrotnie usunąć tego użytkownika?")) {
            return;
        }

        const userId = $(this).data('id');

        $.ajax({
            url: '/admin/users/' + userId,
            method: 'DELETE',
            headers: authHeaders,
            xhrFields: xhrConfig,
            success: function() {
                loadUsers();
            },
            error: function(xhr) {
                alert("Nie udało się usunąć użytkownika. Kod błędu: " + xhr.status);
            }
        });
    });
});