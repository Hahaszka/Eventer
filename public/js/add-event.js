$(document).ready(function () {
  const token = localStorage.getItem("eventer_token");
  const headers = token ? { Authorization: "Bearer " + token } : {};

  $.ajax({
    url: "/users/me",
    method: "GET",
    xhrFields: { withCredentials: true },
    headers: headers,
    success: function (user) {
      initPage(token);
    },
    error: function (xhr) {
      window.location.replace("/auth.html");
    },
  });

  function initPage(authToken) {
    const map = L.map("mapPicker").setView([52.0693, 19.4803], 6);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap",
    }).addTo(map);

    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(function (position) {
        map.setView([position.coords.latitude, position.coords.longitude], 13);
      });
    }

    let currentMarker = null;

    map.on("click", function (e) {
      const lat = e.latlng.lat;
      const lng = e.latlng.lng;

      if (currentMarker) map.removeLayer(currentMarker);
      currentMarker = L.marker([lat, lng]).addTo(map);

      $("#latInput").val(lat);
      $("#lngInput").val(lng);

      $("#locationStatus")
        .removeClass("alert-info")
        .addClass("alert-success")
        .html('<i class="fas fa-check-circle me-2"></i> Lokalizacja wybrana.');

      $("#submitBtn").prop("disabled", false);
    });

    $("#addEventForm").submit(function (e) {
      e.preventDefault();
      $("#formAlert").addClass("d-none");

      const rawDate = $('[name="event_date"]').val();

      if (!rawDate) {
        $("#formAlert").text("Podaj datę wydarzenia!").removeClass("d-none");
        return;
      }

      const isoDate = new Date(rawDate).toISOString();

      const formData = {
        title: $('[name="title"]').val(),
        description: $('[name="description"]').val(),
        category: $('[name="category"]').val(),
        event_date: isoDate,
        latitude: parseFloat($("#latInput").val()),
        longitude: parseFloat($("#lngInput").val()),
      };

      if (!formData.latitude || !formData.longitude) {
        alert("Musisz zaznaczyć lokalizację na mapie!");
        return;
      }

      $.ajax({
        url: "/events/",
        method: "POST",
        contentType: "application/json",
        headers: authToken ? { Authorization: "Bearer " + authToken } : {},
        data: JSON.stringify(formData),
        success: function (newPost) {
          window.location.href = "/dashboard.html";
        },
        error: function (xhr) {
          $("#formAlert").text(Utils.getApiError(xhr)).removeClass("d-none");
        },
      });
    });
  }
});
