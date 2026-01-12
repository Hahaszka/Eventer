$(document).ready(function() {
    
    const token = localStorage.getItem('eventer_token');
    
    const headers = token ? { "Authorization": "Bearer " + token } : {};

    $.ajax({
        url: '/users/me',
        method: 'GET',
        xhrFields: { withCredentials: true }, // Ważne dla Ciasteczek (Google Auth)
        headers: headers,
        success: function(user) {
            console.log("Sesja potwierdzona:", user.email);
            // Dopiero teraz uruchamiamy resztę skryptu
            initPage(token);
        },
        error: function(xhr) {
            console.warn("Brak sesji - przekierowanie.");
            window.location.replace('/auth.html');
        }
    });

    // 2. GŁÓWNA FUNKCJA STRONY (Uruchamiana tylko po weryfikacji)
    function initPage(authToken) {
        
        // --- KONFIGURACJA MAPY (LEAFLET) ---
        // Ustawiamy widok domyślny na Polskę
        const map = L.map('mapPicker').setView([52.0693, 19.4803], 6);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(map);

        // Próba pobrania lokalizacji użytkownika
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(function(position) {
                const userLat = position.coords.latitude;
                const userLng = position.coords.longitude;
                map.setView([userLat, userLng], 13);
            }, function(error) {
                console.log("Brak zgody na lokalizację lub błąd:", error.message);
            });
        }

        let currentMarker = null;

        // --- OBSŁUGA KLIKNIĘCIA W MAPĘ ---
        map.on('click', function(e) {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;

            if (currentMarker) {
                map.removeLayer(currentMarker);
            }

            currentMarker = L.marker([lat, lng]).addTo(map);

            // Uzupełniamy inputy
            $('#latInput').val(lat);
            $('#lngInput').val(lng);

            // UI Feedback
            $('#locationStatus').removeClass('alert-info').addClass('alert-success')
                .html('<i class="fas fa-check-circle me-2"></i> Lokalizacja wybrana.');
            
            $('#submitBtn').prop('disabled', false);
        });

        // --- WYSYŁKA FORMULARZA ---
        $('#addEventForm').submit(function(e) {
            e.preventDefault();

            const formData = {
                title: $('[name="title"]').val(),
                description: $('[name="description"]').val(),
                event_date: $('[name="event_date"]').val(),
                latitude: parseFloat($('#latInput').val()),
                longitude: parseFloat($('#lngInput').val())
            };

            if(!formData.latitude || !formData.longitude) {
                alert("Musisz zaznaczyć lokalizację na mapie!");
                return;
            }

            const submitHeaders = authToken ? { "Authorization": "Bearer " + authToken } : {};

            $.ajax({
                url: '/events/',
                method: 'POST',
                contentType: 'application/json',
                xhrFields: { withCredentials: true },
                headers: submitHeaders,
                data: JSON.stringify(formData),
                success: function(newPost) {
                    window.location.href = '/dashboard.html'; 
                },
                error: function(xhr) {
                    const msg = xhr.responseJSON?.detail || "Błąd dodawania wydarzenia.";
                    $('#formAlert').text(msg).removeClass('d-none');
                }
            });
        });
    }
});