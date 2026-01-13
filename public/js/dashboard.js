$(document).ready(function () {
  const onboardingModal = new bootstrap.Modal(
    document.getElementById("completeProfileModal"),
    { backdrop: "static", keyboard: false }
  );
  const eventViewModal = new bootstrap.Modal(
    document.getElementById("eventViewModal")
  );
  const editEventModal = new bootstrap.Modal(
    document.getElementById("editEventModal")
  );

  // Zmienne globalne
  let map = null;
  let markersCluster = null;
  let allEventsCache = [];
  let userLocation = null;
  let searchTimeout = null;
  let currentUser = null;

  // --- 1. SPRAWDZANIE SESJI ---
  function checkSession() {
    const token = localStorage.getItem("eventer_token");

    $.ajax({
      url: "/users/me",
      method: "GET",
      xhrFields: { withCredentials: true },
      headers: token ? { Authorization: "Bearer " + token } : {},
      success: function (user) {
        currentUser = user;

        const isProfileIncomplete =
          !user.first_name ||
          !user.last_name ||
          !user.username ||
          !user.date_of_birth;

        if (isProfileIncomplete) {
          if (user.first_name) $("#inputFirstName").val(user.first_name);
          if (user.last_name) $("#inputLastName").val(user.last_name);
          if (user.username) $("#inputUsername").val(user.username);
          onboardingModal.show();
        } else {
          initDashboard(user);
        }
      },
      error: function (xhr) {
        if (xhr.status === 401 || xhr.status === 403) {
          window.location.replace("/auth.html");
        }
      },
    });
  }

  function initDashboard(user) {
    $("#navUsername").text(user.username || user.first_name);

    if (user.is_superuser) {
      $("#adminBtn")
        .removeClass("d-none")
        .click(() => (window.location.href = "/admin"));
    }

    initMap();
    initSearch();
    initSorting();
    initCategoryFilter();
  }

  // --- 2. MAPA I LOGIKA POBIERANIA ---
  function initMap() {
    map = L.map("mainMap", { zoomControl: false }).setView(
      [52.0693, 19.4803],
      6
    );

    L.control.zoom({ position: "topright" }).addTo(map);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap",
    }).addTo(map);

    markersCluster = L.markerClusterGroup({
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      disableClusteringAtZoom: 16,
    });
    map.addLayer(markersCluster);

    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition((position) => {
        userLocation = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };

        L.circleMarker([userLocation.lat, userLocation.lng], {
          radius: 8,
          fillColor: "#3388ff",
          color: "#fff",
          weight: 2,
          opacity: 1,
          fillOpacity: 0.8,
        })
          .addTo(map)
          .bindPopup("Twoja lokalizacja");

        map.flyTo([userLocation.lat, userLocation.lng], 12);

        $("#btnSortDistance")
          .prop("disabled", false)
          .attr("title", "Sortuj od najbliższych");
      });
    }

    loadEventsInBounds();
    map.on("moveend", function () {
      loadEventsInBounds();
    });
  }

  // --- GŁÓWNA FUNKCJA POBIERANIA ---
  function loadEventsInBounds() {
    if (!map) return;

    const bounds = map.getBounds();
    const searchQuery = $("#searchInput").val().trim();
    const categoryQuery = $("#categoryFilter").val();

    const queryParams = {
      min_lat: bounds.getSouth(),
      max_lat: bounds.getNorth(),
      min_lng: bounds.getWest(),
      max_lng: bounds.getEast(),
      limit: 150,
    };

    if (searchQuery) {
      queryParams.search = searchQuery;
    }

    if (categoryQuery) {
      queryParams.category = categoryQuery;
    }

    const token = localStorage.getItem("eventer_token");

    $.ajax({
      url: "/events/",
      method: "GET",
      data: queryParams,
      xhrFields: { withCredentials: true },
      headers: token ? { Authorization: "Bearer " + token } : {},

      success: function (events) {
        updateUI(events);
      },
      error: function () {
        console.error("Błąd pobierania danych mapy");
      },
    });
  }

  // --- 3. RENDERING UI ---
  function updateUI(events) {
    const $listContainer = $("#eventsListContainer");
    $listContainer.empty();

    markersCluster.clearLayers();
    allEventsCache = [];

    const countText = events.length >= 150 ? "150+" : events.length;
    $("#eventsCount").text(countText);

    if (events.length === 0) {
      $listContainer.html(
        '<div class="d-flex flex-column align-items-center justify-content-center h-100 text-muted mt-5"><i class="fas fa-map-marked-alt fa-2x mb-3 opacity-50"></i><p>Brak wydarzeń dla tych kryteriów.</p></div>'
      );
      return;
    }

    events.sort((a, b) => new Date(a.event_date) - new Date(b.event_date));

    events.forEach((event) => {
      const marker = createMarker(event);
      markersCluster.addLayer(marker);

      const $card = createCard(event, marker);
      $listContainer.append($card);

      allEventsCache.push({ event, marker, cardElement: $card, dist: 999999 });
    });

    if (userLocation) updateDistancesOnCards();
  }

  function createMarker(event) {
    const dateStr = Utils.formatDate(event.event_date);
    const cat = Utils.getCategoryDetails(event.category);

    const customIcon = L.divIcon({
      className: "custom-map-marker",
      html: `<div style="
            background-color: ${cat.color};
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 3px 8px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 16px;
        "><i class="fas ${cat.icon}"></i></div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 36],
      popupAnchor: [0, -36],
    });

    const marker = L.marker([event.latitude, event.longitude], {
      icon: customIcon,
    });

    const popupContent = `
          <div class="p-2 text-center" style="min-width: 200px;">
              <div class="mb-2">${Utils.getCategoryBadge(event.category)}</div>
              <h6 class="fw-bold mb-1 text-truncate">${Utils.escapeHtml(
                event.title
              )}</h6>
              <div class="text-muted small mb-3"><i class="far fa-clock"></i> ${dateStr}</div>
              <button class="btn btn-sm btn-dark w-100 rounded-pill view-event-btn" data-id="${
                event.id
              }">
                  Szczegóły
              </button>
          </div>`;

    marker.bindPopup(popupContent);
    return marker;
  }

  function createCard(event, marker) {
    const dateStr = Utils.formatDate(event.event_date);
    const timestamp = new Date(event.event_date).getTime();
    const badgeHtml = Utils.getCategoryBadge(event.category);

    const cardHtml = `
        <div class="card event-card border-0 shadow-sm mb-3 rounded-4" 
             id="card-${event.id}" 
             data-date="${timestamp}" 
             data-dist="999999">
            <div class="card-body p-3">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="fw-bold mb-0 text-truncate" style="max-width: 60%;" title="${Utils.escapeHtml(
                      event.title
                    )}">
                        ${Utils.escapeHtml(event.title)}
                    </h6>
                    <div class="d-flex flex-column align-items-end">
                        ${badgeHtml}
                        <span class="dist-badge mt-1"></span>
                    </div>
                </div>
                
                <p class="text-muted small mb-3 text-truncate">
                    ${Utils.escapeHtml(event.description || "Brak opisu")}
                </p>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="badge bg-light text-dark border fw-normal">
                        <i class="far fa-calendar me-1"></i> ${dateStr}
                    </span>
                    <button class="btn btn-sm btn-outline-dark rounded-pill py-0 px-3 view-details-btn" data-id="${
                      event.id
                    }">
                        Info
                    </button>
                </div>
            </div>
        </div>`;

    const $card = $(cardHtml);

    $card.click(function () {
      $(".event-card").removeClass("active");
      $(this).addClass("active");

      map.flyTo([event.latitude, event.longitude], 16, { duration: 1.0 });

      setTimeout(() => {
        markersCluster.zoomToShowLayer(marker, function () {
          marker.openPopup();
        });
      }, 1100);
    });

    return $card;
  }

  // --- 4. FUNKCJE POMOCNICZE ---

  function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * (Math.PI / 180);
    const dLon = (lon2 - lon1) * (Math.PI / 180);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * (Math.PI / 180)) *
        Math.cos(lat2 * (Math.PI / 180)) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  function updateDistancesOnCards() {
    allEventsCache.forEach((item) => {
      const dist = calculateDistance(
        userLocation.lat,
        userLocation.lng,
        item.event.latitude,
        item.event.longitude
      );

      item.dist = dist;
      item.cardElement.attr("data-dist", dist);

      const badgeHtml = `<span class="badge bg-white text-primary border ms-2 small"><i class="fas fa-location-arrow fa-xs me-1"></i>${dist.toFixed(
        1
      )} km</span>`;
      item.cardElement.find(".dist-badge").html(badgeHtml);
    });
  }

  function initSorting() {
    $(".sort-btn").click(function () {
      $(".sort-btn")
        .removeClass("active btn-dark")
        .addClass("btn-outline-dark");
      $(this).removeClass("btn-outline-dark").addClass("active btn-dark");

      const criteria = $(this).data("sort");

      const $container = $("#eventsListContainer");
      const $cards = $container.children(".event-card");

      $cards.sort((a, b) => {
        if (criteria === "date") {
          return $(a).data("date") - $(b).data("date");
        } else if (criteria === "distance") {
          return $(a).data("dist") - $(b).data("dist");
        }
      });

      $cards.detach().appendTo($container);
    });
  }

  function initCategoryFilter() {
    $("#categoryFilter").change(function () {
      loadEventsInBounds();
    });
  }

  function initSearch() {
    $("#searchInput").on("input", function () {
      clearTimeout(searchTimeout);

      searchTimeout = setTimeout(() => {
        loadEventsInBounds();
      }, 500);
    });
  }

  // --- 5. SZCZEGÓŁY WYDARZENIA ---
  $("body").on("click", ".view-event-btn, .view-details-btn", function (e) {
    e.stopPropagation();
    const eventId = $(this).data("id");
    fetchEventDetails(eventId);
  });

  function fetchEventDetails(eventId) {
    const token = localStorage.getItem("eventer_token");

    $("#viewEventTitle").text("Ładowanie...");

    $.ajax({
      url: "/events/" + eventId,
      method: "GET",
      headers: token ? { Authorization: "Bearer " + token } : {},
      success: function (event) {
        $("#viewEventTitle").text(event.title);
        $("#viewEventDesc").text(event.description || "Brak opisu.");
        $("#viewEventDate").text(Utils.formatDate(event.event_date));

        let creatorHtml = '<span class="text-muted">Nieznany</span>';
        if (event.creator) {
          const name =
            event.creator.first_name && event.creator.last_name
              ? `${event.creator.first_name} ${event.creator.last_name}`
              : event.creator.username || "Użytkownik";
          creatorHtml = `<a href="/profile.html?id=${event.creator.id}" class="text-decoration-none fw-bold text-dark hover-underline">${name}</a>`;
        }
        $("#viewEventCreator").html(creatorHtml);

        const isOwner =
          currentUser && event.creator && currentUser.id === event.creator.id;

        $("#btnEditEventTrigger").remove();

        if (isOwner) {
          const $closeBtn = $(
            '#eventViewModal .btn-dark[data-bs-dismiss="modal"]'
          );
          const $editBtn = $(
            `<button id="btnEditEventTrigger" class="btn btn-outline-dark rounded-pill px-4 me-2">Edytuj</button>`
          );

          $editBtn.insertBefore($closeBtn);
          $editBtn.click(function () {
            openEditModal(event);
          });
        }

        eventViewModal.show();
      },
      error: function () {
        alert("Nie udało się pobrać szczegółów.");
      },
    });
  }

  // --- 6. EDYCJA I ONBOARDING ---

  function openEditModal(event) {
    eventViewModal.hide();

    $("#editEventId").val(event.id);
    $("#editEventTitleInput").val(event.title);
    $("#editEventDescInput").val(event.description);
    $("#editEventDateInput").val(Utils.toLocalIsoString(event.event_date));

    $("#editEventCategoryInput").val(event.category || "OTHER");

    editEventModal.show();
  }

  $("#editEventForm").submit(function (e) {
    e.preventDefault();

    const eventId = $("#editEventId").val();
    const rawDate = $("#editEventDateInput").val();

    const updateData = {
      title: $("#editEventTitleInput").val(),
      description: $("#editEventDescInput").val(),
      category: $("#editEventCategoryInput").val(),
      event_date: new Date(rawDate).toISOString(),
    };

    const token = localStorage.getItem("eventer_token");
    $.ajax({
      url: "/events/" + eventId,
      method: "PATCH",
      contentType: "application/json",
      headers: token ? { Authorization: "Bearer " + token } : {},
      data: JSON.stringify(updateData),
      success: function (updatedEvent) {
        editEventModal.hide();
        loadEventsInBounds();
      },
      error: function (xhr) {
        alert("Błąd zapisu: " + Utils.getApiError(xhr));
      },
    });
  });

  $("#onboardingForm").submit(function (e) {
    e.preventDefault();
    const updateData = {
      first_name: $("#inputFirstName").val(),
      last_name: $("#inputLastName").val(),
      username: $("#inputUsername").val(),
      date_of_birth: $("#inputDob").val(),
      gender: $("#inputGender").val(),
    };
    const token = localStorage.getItem("eventer_token");
    $.ajax({
      url: "/users/me",
      method: "PATCH",
      contentType: "application/json",
      xhrFields: { withCredentials: true },
      headers: token ? { Authorization: "Bearer " + token } : {},
      data: JSON.stringify(updateData),
      success: function (updatedUser) {
        currentUser = updatedUser;
        onboardingModal.hide();
        initDashboard(updatedUser);
      },
      error: function (xhr) {
        alert("Błąd zapisu: " + Utils.getApiError(xhr));
      },
    });
  });

  $("#logoutBtn").click(function (e) {
    e.preventDefault();
    localStorage.removeItem("eventer_token");
    $.post("/auth/logout").always(() => window.location.replace("/auth.html"));
  });

  checkSession();
});
